from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings


def _make_engine(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            future=True,
            connect_args={"check_same_thread": False, "timeout": 30},
            poolclass=StaticPool,
        )
    return create_engine(database_url, future=True)


engine = _make_engine(settings.database_url)
try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
except Exception:
    settings.database_url = "sqlite:///./ai_usage_monitor.db"
    engine = _make_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
