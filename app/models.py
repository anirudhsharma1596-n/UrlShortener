# app/models.py
from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(10), unique=True, index=True, nullable=False)
    original_url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    click_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    clicks = relationship("Click", back_populates="url", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_short_code_active", "short_code", "is_active"),
    )


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete="CASCADE"), nullable=False)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(String(45), nullable=True)
    country = Column(String(100), nullable=True)
    user_agent = Column(Text, nullable=True)
    referer = Column(Text, nullable=True)

    # ── New columns ───────────────────────────────────────────
    browser = Column(String(100), nullable=True)   # "Chrome", "Firefox", "Safari"
    os = Column(String(100), nullable=True)        # "Mac OS X", "Windows", "Android"

    url = relationship("URL", back_populates="clicks")

    __table_args__ = (
        Index("idx_clicks_url_id", "url_id"),
    )