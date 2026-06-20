from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    remark: Optional[str] = None
    contacts: list[str] = Field(default_factory=list)

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value):
        if value in (None, "", "男", "女", "保密"):
            return value or None
        raise ValueError("性别只能是男、女、保密")

    @field_validator("contacts", mode="before")
    @classmethod
    def normalize_contacts(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        return value


class UserCreate(UserBase):
    password: str


class UserAdminCreate(UserCreate):
    is_active: bool = True
    is_admin: bool = False
    department_ids: list[int] = Field(default_factory=list)
    role_ids: list[int] = Field(default_factory=list)
    position_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    nickname: Optional[str] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    remark: Optional[str] = None
    contacts: Optional[list[str]] = None
    password: Optional[str] = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value):
        if value in (None, "", "男", "女", "保密"):
            return value or None
        raise ValueError("性别只能是男、女、保密")


class UserAdminUpdate(UserUpdate):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_deleted: Optional[bool] = None
    department_ids: Optional[list[int]] = None
    role_ids: Optional[list[int]] = None
    position_ids: Optional[list[int]] = None


class UserBatchDelete(BaseModel):
    user_ids: list[int] = Field(default_factory=list)


class UserResetPassword(BaseModel):
    password: str


class UserAssignRoles(BaseModel):
    role_ids: list[int] = Field(default_factory=list)


class UserRead(UserBase):
    id: int
    is_active: bool
    is_deleted: bool
    is_admin: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
