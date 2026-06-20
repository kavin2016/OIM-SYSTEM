from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PermissionBase(BaseModel):
    name: str
    code: str
    parent_id: Optional[int] = None
    type: str = "button"
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int = 0
    description: Optional[str] = None


class PermissionCreate(PermissionBase):
    is_active: bool = True


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_id: Optional[int] = None
    type: Optional[str] = None
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None


class PermissionRead(PermissionBase):
    id: int
    is_active: bool
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
