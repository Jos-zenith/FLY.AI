from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

def _make_engine(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(database_url, future=True, connect_args={"check_same_thread": False})
    return create_engine(database_url, future=True)


engine = _make_engine(settings.database_url)

try:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
except Exception:
    settings.database_url = "sqlite:///./betty.db"
    engine = _make_engine(settings.database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
