from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PositionBase(BaseModel):
    code: str
    name: str
    sort_order: int = 0
    status: int = Field(default=0, ge=0, le=1)
    remark: Optional[str] = None


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    sort_order: Optional[int] = None
    status: Optional[int] = Field(default=None, ge=0, le=1)
    is_deleted: Optional[bool] = None
    remark: Optional[str] = None


class PositionRead(PositionBase):
    id: int
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
