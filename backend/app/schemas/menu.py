from typing import Optional

from pydantic import BaseModel


class MenuItem(BaseModel):
    id: int
    parent_id: Optional[int] = None
    name: str
    code: str
    path: Optional[str] = None
    component: Optional[str] = None
    icon: Optional[str] = None
    sort_order: int
    children: list["MenuItem"] = []

    model_config = {"from_attributes": True}

