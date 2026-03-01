# app/schemas.py
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


class URLCreate(BaseModel):
    original_url: HttpUrl
    custom_code: Optional[str] = Field(None, min_length=3, max_length=10)
    expires_at: Optional[datetime] = None


class URLResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime]
    click_count: int
    is_active: bool

    model_config = {"from_attributes": True}


# ── Analytics schemas ──────────────────────────────────────────

class DailyClick(BaseModel):
    date: str          # "2024-01-01"
    count: int

class RefererStat(BaseModel):
    referer: str
    count: int

class BrowserStat(BaseModel):
    browser: str
    count: int

class CountryStat(BaseModel):
    country: str
    count: int

class ClickStats(BaseModel):
    total_clicks: int
    clicks_today: int
    clicks_by_day: list[DailyClick]
    top_referers: list[RefererStat]
    top_browsers: list[BrowserStat]
    top_countries: list[CountryStat]

class URLAnalytics(BaseModel):
    url: URLResponse
    stats: ClickStats