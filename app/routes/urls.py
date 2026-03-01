# app/routes/urls.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app import models
from app.schemas import URLCreate, URLResponse
from app.utils.shortcode import generate_short_code
from app.config import settings
from app.cache import cache_url, get_cached_url, invalidate_url_cache  # ← new
from app.utils.user_agent import extract_browser, extract_os
from app.utils.rate_limiter import (   # ← new
    check_rate_limit,
    create_url_limiter,
    redirect_limiter
)


router = APIRouter()


@router.post("/urls", response_model=URLResponse, 
             status_code=201
            ,dependencies=[Depends(check_rate_limit(create_url_limiter))] )
def create_short_url(payload: URLCreate, db: Session = Depends(get_db)):
    # No changes here — caching on create isn't necessary
    # The first GET will populate the cache
    if payload.custom_code:
        existing = db.query(models.URL).filter(
            models.URL.short_code == payload.custom_code
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"Code '{payload.custom_code}' is already taken")
        short_code = payload.custom_code
    else:
        for _ in range(5):
            short_code = generate_short_code()
            exists = db.query(models.URL).filter(
                models.URL.short_code == short_code
            ).first()
            if not exists:
                break
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique code, try again")

    url = models.URL(
        short_code=short_code,
        original_url=str(payload.original_url),
        expires_at=payload.expires_at,
    )
    db.add(url)
    db.commit()
    db.refresh(url)

    url.short_url = f"{settings.BASE_URL}/{url.short_code}"
    return url


@router.get("/{short_code}",dependencies=[Depends(check_rate_limit(redirect_limiter))])
def redirect_to_url(short_code: str, request: Request, db: Session = Depends(get_db)):

    original_url = None   # what we'll ultimately redirect to

    # ── Step 1: Check Redis first ──────────────────────────────
    cached = get_cached_url(short_code)

    if cached:
        # Cache hit — we have everything we need, skip the DB
        # Still need to check expiry even from cache
        if cached.get("expires_at"):
            expires_at = datetime.fromisoformat(cached["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                raise HTTPException(status_code=410, detail="This short URL has expired")

        original_url = cached["original_url"]
        url_id = cached["id"]

    else:
        # ── Step 2: Cache miss — go to PostgreSQL ──────────────
        url = db.query(models.URL).filter(
            models.URL.short_code == short_code,
            models.URL.is_active == True
        ).first()

        if not url:
            raise HTTPException(status_code=404, detail="Short URL not found")

        if url.expires_at and url.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=410, detail="This short URL has expired")

        # ── Step 3: Populate the cache for next time ───────────
        cache_url(
            short_code=short_code,
            url_data={
                "id": url.id,
                "original_url": url.original_url,
                "expires_at": url.expires_at.isoformat() if url.expires_at else None,
            },
            ttl_seconds=settings.CACHE_TTL_SECONDS
        )

        original_url = url.original_url
        url_id = url.id

    # ── Step 4: Record the click (always hits DB — that's fine) ─
    # Analytics writes are less critical than redirect reads
    raw_user_agent = request.headers.get("user-agent")

    click = models.Click(
        url_id=url_id,
        ip_address=request.client.host,
        user_agent=raw_user_agent,
        referer=request.headers.get("referer"),
        browser=extract_browser(raw_user_agent),   # ← parse and store clean value
        os=extract_os(raw_user_agent),             # ← parse and store clean value
    )
    db.add(click)

    # Update denormalized count
    db.query(models.URL).filter(models.URL.id == url_id).update(
        {"click_count": models.URL.click_count + 1}
    )
    db.commit()

    return RedirectResponse(url=original_url, status_code=307)


@router.delete("/urls/{short_code}", status_code=204)
def delete_url(short_code: str, db: Session = Depends(get_db)):
    url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    url.is_active = False
    db.commit()

    # ── Invalidate cache so Redis doesn't serve a deleted URL ──
    invalidate_url_cache(short_code)

    return None
