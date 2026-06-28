from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request

from ..dependencies import LoginLogServiceDep, OperationLogServiceDep
from ..schemas.login_log import LoginLogDetail, LoginLogExport, LoginLogOptions, LoginLogRead
from ..security import require_permission
from ..services.data_scope import ensure_user_in_scope, scoped_user_ids

router = APIRouter(prefix="/login-logs", tags=["login-logs"])


@router.get("/options", response_model=LoginLogOptions)
def list_login_log_options(
    login_log_service: LoginLogServiceDep,
    current_user=Depends(require_permission("ops:login-log:query")),
):
    return login_log_service.options()


@router.get("", response_model=list[LoginLogRead])
def list_login_logs(
    login_log_service: LoginLogServiceDep,
    skip: int = 0,
    limit: int = 100,
    cursor_id: Optional[int] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    login_type: Optional[str] = None,
    result: Optional[str] = None,
    client_ip: Optional[str] = None,
    created_at_start: Optional[datetime] = None,
    created_at_end: Optional[datetime] = None,
    keyword: Optional[str] = None,
    current_user=Depends(require_permission("ops:login-log:query")),
):
    scope_ids = scoped_user_ids(login_log_service.db, current_user, user_id=user_id, department_id=department_id)
    return login_log_service.list(
        skip=skip,
        limit=limit,
        cursor_id=cursor_id,
        user_id=user_id,
        username=username,
        department_id=department_id,
        department_name=department_name,
        login_type=login_type,
        result=result,
        client_ip=client_ip,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        keyword=keyword,
        scope_user_ids=scope_ids,
    )


@router.get("/export", response_model=LoginLogExport)
def export_login_logs(
    request: Request,
    login_log_service: LoginLogServiceDep,
    operation_log_service: OperationLogServiceDep,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    login_type: Optional[str] = None,
    result: Optional[str] = None,
    client_ip: Optional[str] = None,
    created_at_start: Optional[datetime] = None,
    created_at_end: Optional[datetime] = None,
    keyword: Optional[str] = None,
    current_user=Depends(require_permission("ops:login-log:export")),
):
    scope_ids = scoped_user_ids(login_log_service.db, current_user, user_id=user_id, department_id=department_id)
    filename, content = login_log_service.export_csv(
        user_id=user_id,
        username=username,
        department_id=department_id,
        department_name=department_name,
        login_type=login_type,
        result=result,
        client_ip=client_ip,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        keyword=keyword,
        scope_user_ids=scope_ids,
    )
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="login_log",
        action="export",
        action_name="导出登录日志",
        request=request,
        response_params={"filename": filename, "rows_limit": 10000},
    )
    return {"filename": filename, "content": content}


@router.get("/{log_id}", response_model=LoginLogDetail)
def get_login_log(
    log_id: int,
    login_log_service: LoginLogServiceDep,
    current_user=Depends(require_permission("ops:login-log:detail")),
):
    item = login_log_service.get_required(log_id)
    ensure_user_in_scope(login_log_service.db, current_user, item.user_id, detail="无权查看该登录日志")
    return item
