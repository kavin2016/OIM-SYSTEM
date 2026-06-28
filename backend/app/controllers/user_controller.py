from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request, status

from ..dependencies import OperationLogServiceDep, UserServiceDep
from ..schemas.department import DepartmentRead
from ..schemas.position import PositionRead
from ..schemas.role import RoleRead
from ..schemas.user import (
    UserAdminCreate,
    UserAdminUpdate,
    UserAssignRoles,
    UserBatchDelete,
    UserRead,
    UserResetPassword,
    UserUpdate,
)
from ..security import get_current_active_user, require_permission
from ..services.data_scope import ensure_departments_in_scope, ensure_user_in_scope, scoped_user_ids

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user=Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    request: Request,
    user_update: UserUpdate,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(get_current_active_user),
):
    item = user_service.update_user(current_user, user_update, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        resource_id=item.id,
        resource_name=item.username,
        action="update",
        action_name="修改个人资料",
        request=request,
        request_body=user_update,
        response_params={"id": item.id, "username": item.username},
    )
    return item


@router.get("", response_model=list[UserRead])
def list_users(
    user_service: UserServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    username: Optional[str] = None,
    nickname: Optional[str] = None,
    is_active: Optional[bool] = None,
    department_id: Optional[int] = None,
    role_id: Optional[int] = None,
    created_at_start: Optional[datetime] = None,
    created_at_end: Optional[datetime] = None,
    current_user=Depends(require_permission("system:user:query")),
):
    scope_ids = scoped_user_ids(user_service.db, current_user, department_id=department_id)
    return user_service.list(
        skip=skip,
        limit=limit,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
        username=username,
        nickname=nickname,
        is_active=is_active,
        department_id=department_id,
        role_id=role_id,
        created_at_start=created_at_start,
        created_at_end=created_at_end,
        scope_user_ids=scope_ids,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user_create: UserAdminCreate,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:user:create")),
):
    ensure_departments_in_scope(user_service.db, current_user, user_create.department_ids)
    ensure_departments_in_scope(user_service.db, current_user, user_create.data_scope_department_ids)
    item = user_service.create_admin_user(user_create, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        resource_id=item.id,
        resource_name=item.username,
        action="create",
        action_name="新增用户",
        request=request,
        request_body=user_create,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "username": item.username},
    )
    return item


@router.post("/batch-delete", response_model=list[UserRead])
def batch_delete_users(
    request: Request,
    payload: UserBatchDelete,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:user:delete")),
):
    for user_id in payload.user_ids:
        ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权删除该用户")
    items = user_service.delete_users(payload.user_ids, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        action="delete",
        action_name="批量禁用用户",
        request=request,
        request_body=payload,
        response_params={"ids": [item.id for item in items], "count": len(items)},
    )
    return items


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_user_password(
    request: Request,
    user_id: int,
    payload: UserResetPassword,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:user:reset-password")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权重置该用户密码")
    item = user_service.reset_password(user_id, payload.password, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        resource_id=item.id,
        resource_name=item.username,
        action="reset-password",
        action_name="重置密码",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "username": item.username},
    )
    return item


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    user_service: UserServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:user:query")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id)
    return user_service.get_required(user_id, include_deleted=include_deleted)


@router.get("/{user_id}/departments", response_model=list[DepartmentRead])
def list_user_departments(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:query")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id)
    return user_service.list_departments(user_id)


@router.get("/{user_id}/data-scope-departments", response_model=list[DepartmentRead])
def list_user_data_scope_departments(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:assign-role")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权查看该用户数据范围")
    return user_service.list_data_scope_departments(user_id)


@router.get("/{user_id}/roles", response_model=list[RoleRead])
def list_user_roles(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:assign-role")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权查看该用户角色")
    return user_service.list_roles(user_id)


@router.get("/{user_id}/positions", response_model=list[PositionRead])
def list_user_positions(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:query")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id)
    return user_service.list_positions(user_id)


@router.put("/{user_id}/roles", response_model=UserRead)
def assign_user_roles(
    request: Request,
    user_id: int,
    payload: UserAssignRoles,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:user:assign-role")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权分配该用户角色")
    if payload.data_scope_department_ids is not None:
        ensure_departments_in_scope(user_service.db, current_user, payload.data_scope_department_ids)
    item = user_service.assign_roles(
        user_id,
        payload.role_ids,
        actor_id=current_user.id,
        data_scope_department_ids=payload.data_scope_department_ids,
    )
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        resource_id=item.id,
        resource_name=item.username,
        action="assign-role",
        action_name="分配角色",
        request=request,
        request_body=payload,
        response_params={
            "id": item.id,
            "username": item.username,
            "role_ids": payload.role_ids,
            "data_scope_department_ids": payload.data_scope_department_ids,
        },
    )
    return item


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    request: Request,
    user_id: int,
    user_update: UserAdminUpdate,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:user:update")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权修改该用户")
    if user_update.department_ids is not None:
        ensure_departments_in_scope(user_service.db, current_user, user_update.department_ids)
    if user_update.data_scope_department_ids is not None:
        ensure_departments_in_scope(user_service.db, current_user, user_update.data_scope_department_ids)
    item = user_service.update_admin_user(user_id, user_update, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        resource_id=item.id,
        resource_name=item.username,
        action="update",
        action_name="修改用户",
        request=request,
        request_body=user_update,
        response_params={"id": item.id, "username": item.username},
    )
    return item


@router.delete("/{user_id}", response_model=UserRead)
def disable_user(
    request: Request,
    user_id: int,
    user_service: UserServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:user:delete")),
):
    ensure_user_in_scope(user_service.db, current_user, user_id, detail="无权删除该用户")
    item = user_service.delete_user(user_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="user",
        resource_id=item.id,
        resource_name=item.username,
        action="delete",
        action_name="禁用用户",
        request=request,
        response_params={"id": item.id, "username": item.username},
    )
    return item
