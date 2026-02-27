# app/routes/urls.py
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import update
from datetime import datetime, timezone

from app.database import get_db
from app import models
from app.schemas import URLCreate, URLResponse
from app.utils.shortcode import generate_short_code
from app.config import settings

router = APIRouter()


# ─────────────────────────────────────────
# POST /urls  — Create a short URL
# ─────────────────────────────────────────
@router.post("/urls", response_model=URLResponse, status_code=201)
def create_short_url(payload: URLCreate, db: Session = Depends(get_db)):
    """
    Receives a long URL, returns a short one.
    
    FastAPI automatically:
    - Parses the JSON body into a URLCreate object
    - Validates all fields (HttpUrl check, length limits)
    - Returns 422 with clear errors if validation fails
    """

    # Handle custom code if user provided one
    if payload.custom_code:
        # Check if this custom code is already taken
        existing = db.query(models.URL).filter(
            models.URL.short_code == payload.custom_code
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,   # 409 Conflict
                detail=f"Code '{payload.custom_code}' is already taken"
            )
        short_code = payload.custom_code

    else:
        # Auto-generate a unique code
        # Keep trying until we get one that doesn't exist
        # In practice this loop runs once — collisions are rare
        for _ in range(5):   # max 5 attempts
            short_code = generate_short_code()
            exists = db.query(models.URL).filter(
                models.URL.short_code == short_code
            ).first()
            if not exists:
                break
        else:
            # 'else' on a for loop runs if we never hit 'break'
            raise HTTPException(
                status_code=500,
                detail="Could not generate unique code, try again"
            )

    # Create the database record
    url = models.URL(
        short_code=short_code,
        original_url=str(payload.original_url),  # convert HttpUrl to plain string
        expires_at=payload.expires_at,
    )
    db.add(url)
    db.commit()
    db.refresh(url)   # reload from DB so we get the generated id, created_at etc.

    # Construct the full short URL to return
    # We add this field that doesn't exist in the DB
    url.short_url = f"{settings.BASE_URL}/{url.short_code}"

    return url


# ─────────────────────────────────────────
# GET /{short_code}  — Redirect to original URL
# ─────────────────────────────────────────
@router.get("/{short_code}")
def redirect_to_url(short_code: str, request: Request, db: Session = Depends(get_db)):
    """
    The core feature — someone visits /aB3xZ9 and gets sent to the original URL.
    We also record the click for analytics.
    """

    # Look up the short code
    url = db.query(models.URL).filter(
        models.URL.short_code == short_code,
        models.URL.is_active == True
    ).first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Check if the URL has expired
    if url.expires_at and url.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="This short URL has expired")
        # 410 Gone — more accurate than 404, means "existed but no longer available"

    # Record the click (we'll expand this with more data in Phase 5)
    click = models.Click(
        url_id=url.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
    )
    db.add(click)

    # Increment the denormalized click counter on the URL itself
    url.click_count += 1
    db.commit()

    # 307 Temporary Redirect — tells browsers "this is intentional,
    # but don't cache it permanently" (unlike 301 which browsers cache forever)
    return RedirectResponse(url=url.original_url, status_code=307)


# ─────────────────────────────────────────
# DELETE /urls/{short_code}  — Deactivate a URL
# ─────────────────────────────────────────
@router.delete("/urls/{short_code}", status_code=204)
def delete_url(short_code: str, db: Session = Depends(get_db)):
    """
    We don't actually delete the row — we set is_active=False.
    This preserves click history for analytics.
    This pattern is called a 'soft delete'.
    """

    url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    url.is_active = False
    db.commit()

    # 204 No Content — success, but nothing to return
    return None