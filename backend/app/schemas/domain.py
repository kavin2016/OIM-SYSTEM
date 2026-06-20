from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class DomainBase(BaseModel):
    code: str
    name: str
    registrar: Optional[str] = None
    expiry_date: Optional[date] = None
    sort_order: int = 0
    status: int = Field(default=0, ge=0, le=1)
    remark: Optional[str] = None


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    registrar: Optional[str] = None
    expiry_date: Optional[date] = None
    sort_order: Optional[int] = None
    status: Optional[int] = Field(default=None, ge=0, le=1)
    is_deleted: Optional[bool] = None
    remark: Optional[str] = None


class DomainRead(DomainBase):
    id: int
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
