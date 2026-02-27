# app/schemas.py
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


# --- Request schemas (what the client sends us) ---

class URLCreate(BaseModel):
    original_url: HttpUrl                          # Pydantic validates this is a real URL
    custom_code: Optional[str] = Field(           # Optional: let user pick their code
        None, min_length=3, max_length=10
    )
    expires_at: Optional[datetime] = None


# --- Response schemas (what we send back) ---

class URLResponse(BaseModel):
    id: int
    short_code: str
    original_url: str
    short_url: str                                 # We'll construct this: BASE_URL/short_code
    created_at: datetime
    expires_at: Optional[datetime]
    click_count: int
    is_active: bool

    # This tells Pydantic to read data from SQLAlchemy model attributes
    # Without this, Pydantic wouldn't know how to read ORM objects
    model_config = {"from_attributes": True}


class ClickStats(BaseModel):
    total_clicks: int
    clicks_today: int
    top_referers: list[dict]
    recent_clicks: list[dict]


class URLAnalytics(BaseModel):
    url: URLResponse
    stats: ClickStats