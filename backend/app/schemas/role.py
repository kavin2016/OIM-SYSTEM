from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RoleBase(BaseModel):
    name: str
    code: str
    sort_order: int = 0
    description: Optional[str] = None


class RoleCreate(RoleBase):
    is_active: bool = True
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None
    permission_ids: Optional[list[int]] = None


class RoleRead(RoleBase):
    id: int
    sort_order: int
    is_active: bool
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
