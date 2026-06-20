from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import get_database_url, settings

engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_recycle=settings.mysql_pool_recycle_seconds,
    pool_size=10,
    max_overflow=20,
    pool_timeout=10,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
