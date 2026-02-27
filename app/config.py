# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # These names must exactly match your .env file keys
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_HOST: str
    REDIS_PORT: int

    APP_SECRET_KEY: str
    BASE_URL: str

    class Config:
        env_file = ".env"

# Create one instance — imported everywhere that needs config
# This reads .env once at startup, not on every import
settings = Settings()