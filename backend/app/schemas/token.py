from pydantic import BaseModel

from .menu import MenuItem
from .user import UserRead


class Token(BaseModel):
    access_token: str
    token_type: str


class AuthSession(BaseModel):
    user: UserRead
    menus: list[MenuItem]
    permissions: list[str]
