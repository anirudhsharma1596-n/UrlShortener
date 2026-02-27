# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# The connection string tells SQLAlchemy HOW to connect to PostgreSQL
# Format: postgresql://user:password@host:port/database_name
DATABASE_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)

# The engine is the actual connection pool to the database
# pool_pre_ping=True means "check if connection is alive before using it"
# This prevents errors if the DB restarted and the connection went stale
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# A SessionLocal is a factory that creates database sessions
# Each request gets its own session — like a transaction wrapper
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that all our models will inherit from
# SQLAlchemy uses this to know which classes represent database tables
class Base(DeclarativeBase):
    pass


# Dependency — FastAPI will call this for every request that needs DB access
# It creates a session, yields it to the route, then closes it when done
# The try/finally ensures the session closes even if an error occurs
def get_db():
    db = SessionLocal()
    try:
        yield db          # ← 'yield' makes this a generator (dependency injection)
    finally:
        db.close()