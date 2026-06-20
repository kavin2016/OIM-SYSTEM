from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    code: str
    parent_id: Optional[int] = None
    description: Optional[str] = None


class DepartmentCreate(DepartmentBase):
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None


class DepartmentRead(DepartmentBase):
    id: int
    is_active: bool
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
