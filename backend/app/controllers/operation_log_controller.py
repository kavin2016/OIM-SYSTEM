from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request

from ..dependencies import OperationLogServiceDep
from ..schemas.operation_log import OperationLogDetail, OperationLogExport, OperationLogOptions, OperationLogRead
from ..security import require_permission

router = APIRouter(prefix="/operation-logs", tags=["operation-logs"])


@router.get("/options", response_model=OperationLogOptions)
def list_operation_log_options(
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:operation-log:query")),
):
    return operation_log_service.options()


@router.get("", response_model=list[OperationLogRead])
def list_operation_logs(
    operation_log_service: OperationLogServiceDep,
    skip: int = 0,
    limit: int = 100,
    cursor_id: Optional[int] = None,
    operator_id: Optional[int] = None,
    operator_username: Optional[str] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    module: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    client_ip: Optional[str] = None,
    created_at_start: Optional[datetime] = None,
    created_at_end: Optional[datetime] = None,
    keyword: Optional[str] = None,
    current_user=Depends(require_permission("ops:operation-log:query")),
):
    return operation_log_service.list(
        skip=skip,
        limit=limit,
        cursor_id=cursor_id,
        operator_id=operator_id,
        operator_username=operator_username,
        department_id=department_id,
        department_name=department_name,
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        result=result,
        client_ip=client_ip,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        keyword=keyword,
    )


@router.get("/export", response_model=OperationLogExport)
def export_operation_logs(
    request: Request,
    operation_log_service: OperationLogServiceDep,
    operator_id: Optional[int] = None,
    operator_username: Optional[str] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    module: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    client_ip: Optional[str] = None,
    created_at_start: Optional[datetime] = None,
    created_at_end: Optional[datetime] = None,
    keyword: Optional[str] = None,
    current_user=Depends(require_permission("ops:operation-log:export")),
):
    filename, content = operation_log_service.export_csv(
        operator_id=operator_id,
        operator_username=operator_username,
        department_id=department_id,
        department_name=department_name,
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        result=result,
        client_ip=client_ip,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        keyword=keyword,
    )
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="operation_log",
        action="export",
        action_name="导出操作日志",
        request=request,
        response_params={"filename": filename, "rows_limit": 10000},
    )
    return {"filename": filename, "content": content}


@router.get("/{log_id}", response_model=OperationLogDetail)
def get_operation_log(
    log_id: int,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:operation-log:detail")),
):
    return operation_log_service.get_required(log_id)
