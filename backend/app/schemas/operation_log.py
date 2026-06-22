from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class OperationLogRead(BaseModel):
    id: int
    trace_id: Optional[str] = None
    operator_id: Optional[int] = None
    operator_username: Optional[str] = None
    operator_nickname: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    module: str
    module_name: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    resource_name: Optional[str] = None
    action: str
    action_name: str
    response_status: Optional[int] = None
    result: str
    client_ip: Optional[str] = None
    duration_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OperationLogDetail(OperationLogRead):
    method: Optional[str] = None
    path: Optional[str] = None
    request_params: Optional[dict[str, Any]] = None
    request_body: Optional[dict[str, Any]] = None
    response_params: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    user_agent: Optional[str] = None


class OperationLogExport(BaseModel):
    filename: str
    content: str


class OperationLogOptionItem(BaseModel):
    value: str
    label: str


class OperationLogOptions(BaseModel):
    modules: list[OperationLogOptionItem]
    resource_types: list[OperationLogOptionItem]
    actions: list[OperationLogOptionItem]
    results: list[OperationLogOptionItem]
