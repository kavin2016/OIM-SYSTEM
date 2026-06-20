from fastapi import APIRouter
from sqlalchemy import text

from ..dependencies import DbSession

router = APIRouter(tags=["health"])


@router.get("/ping")
def ping():
    return {"message": "pong"}


@router.get("/health/db")
def database_health(db: DbSession):
    row = db.execute(text("SELECT DATABASE()")).scalar()
    return {"database": row, "status": "ok"}

