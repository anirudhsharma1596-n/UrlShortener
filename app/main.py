# app/main.py
from fastapi import FastAPI
from app.database import engine, Base
from app import models
from app.routes import urls,analytics   # noqa — import triggers model registration with Base

app = FastAPI(
    title="URL Shortener",
    description="A URL shortening service with analytics",
    version="1.0.0"
)

app.include_router(urls.router)
app.include_router(analytics.router)

# Creates all tables that don't exist yet
# In production you'd use Alembic migrations instead — but this is fine for now
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

