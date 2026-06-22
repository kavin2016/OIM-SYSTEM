from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class LoginLogRead(BaseModel):
    id: int
    trace_id: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    nickname: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    login_type: str
    response_status: Optional[int] = None
    result: str
    error_message: Optional[str] = None
    client_ip: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginLogDetail(LoginLogRead):
    method: Optional[str] = None
    path: Optional[str] = None
    request_params: Optional[dict[str, Any]] = None
    request_body: Optional[dict[str, Any]] = None
    response_params: Optional[dict[str, Any]] = None
    user_agent: Optional[str] = None


class LoginLogExport(BaseModel):
    filename: str
    content: str


class LoginLogOptionItem(BaseModel):
    value: str
    label: str


class LoginLogOptions(BaseModel):
    results: list[LoginLogOptionItem]
    login_types: list[LoginLogOptionItem]
