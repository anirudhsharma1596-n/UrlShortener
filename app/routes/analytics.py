# app/routes/analytics.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import datetime, timezone

from app.database import get_db
from app import models
from app.schemas import URLAnalytics, URLResponse, ClickStats
from app.config import settings
from app.utils.rate_limiter import check_rate_limit, analytics_limiter


router = APIRouter()


@router.get("/urls/{short_code}/analytics", 
            response_model=URLAnalytics,
            dependencies=[Depends(check_rate_limit(analytics_limiter))] )
def get_url_analytics(short_code: str, db: Session = Depends(get_db)):

    # Fetch the URL — must exist and be active
    url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # ── Query 1: Total clicks ──────────────────────────────────
    # We already have this on the URL row — no extra query needed!
    total_clicks = url.click_count

    # ── Query 2: Clicks today ──────────────────────────────────
    today = datetime.now(timezone.utc).date()

    clicks_today = db.query(func.count(models.Click.id)).filter(
        models.Click.url_id == url.id,
        # cast to Date strips the time portion for comparison
        cast(models.Click.clicked_at, Date) == today
    ).scalar()   # .scalar() returns a single value instead of a row

    # ── Query 3: Clicks by day (last 30 days) ─────────────────
    # GROUP BY the date portion of clicked_at, count rows per group
    # This is the SQL equivalent of:
    # SELECT DATE(clicked_at), COUNT(*) FROM clicks
    # WHERE url_id = X GROUP BY DATE(clicked_at) ORDER BY date
    clicks_by_day_rows = db.query(
        cast(models.Click.clicked_at, Date).label("date"),
        func.count(models.Click.id).label("count")
    ).filter(
        models.Click.url_id == url.id
    ).group_by(
        cast(models.Click.clicked_at, Date)
    ).order_by(
        cast(models.Click.clicked_at, Date)
    ).limit(30).all()

    clicks_by_day = [
        {"date": str(row.date), "count": row.count}
        for row in clicks_by_day_rows
    ]

    # ── Query 4: Top referers ──────────────────────────────────
    # Where is traffic coming from?
    top_referers_rows = db.query(
        models.Click.referer,
        func.count(models.Click.id).label("count")
    ).filter(
        models.Click.url_id == url.id,
        models.Click.referer.isnot(None)   # ignore direct traffic (no referer)
    ).group_by(
        models.Click.referer
    ).order_by(
        func.count(models.Click.id).desc()  # most clicks first
    ).limit(10).all()

    top_referers = [
        {"referer": row.referer or "Direct", "count": row.count}
        for row in top_referers_rows
    ]

    # ── Query 5: Top browsers ──────────────────────────────────
    top_browsers_rows = db.query(
        models.Click.browser,
        func.count(models.Click.id).label("count")
    ).filter(
        models.Click.url_id == url.id,
        models.Click.browser.isnot(None)
    ).group_by(
        models.Click.browser
    ).order_by(
        func.count(models.Click.id).desc()
    ).limit(5).all()

    top_browsers = [
        {"browser": row.browser or "Unknown", "count": row.count}
        for row in top_browsers_rows
    ]

    # ── Query 6: Top countries ─────────────────────────────────
    top_countries_rows = db.query(
        models.Click.country,
        func.count(models.Click.id).label("count")
    ).filter(
        models.Click.url_id == url.id,
        models.Click.country.isnot(None)
    ).group_by(
        models.Click.country
    ).order_by(
        func.count(models.Click.id).desc()
    ).limit(10).all()

    top_countries = [
        {"country": row.country or "Unknown", "count": row.count}
        for row in top_countries_rows
    ]

    # ── Assemble the response ──────────────────────────────────
    url.short_url = f"{settings.BASE_URL}/{url.short_code}"

    stats = ClickStats(
        total_clicks=total_clicks,
        clicks_today=clicks_today or 0,
        clicks_by_day=clicks_by_day,
        top_referers=top_referers,
        top_browsers=top_browsers,
        top_countries=top_countries,
    )

    return URLAnalytics(url=URLResponse.model_validate(url), stats=stats)