from typing import Optional

from fastapi import APIRouter, Depends, Request, status

from ..dependencies import OperationLogServiceDep, RoleServiceDep
from ..schemas.permission import RolePermissionRead
from ..schemas.role import RoleCreate, RoleRead, RoleUpdate
from ..security import require_permission

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
def list_roles(
    role_service: RoleServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    name: Optional[str] = None,
    code: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user=Depends(require_permission("system:role:query")),
):
    return role_service.list(
        skip=skip,
        limit=limit,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
        name=name,
        code=code,
        is_active=is_active,
    )


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(
    request: Request,
    role_create: RoleCreate,
    role_service: RoleServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:role:create")),
):
    item = role_service.create_item(role_create, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="role",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增角色",
        request=request,
        request_body=role_create,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.get("/{role_id}", response_model=RoleRead)
def get_role(
    role_id: int,
    role_service: RoleServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:role:query")),
):
    return role_service.get_required(role_id, include_deleted=include_deleted)


@router.get("/{role_id}/permissions", response_model=list[RolePermissionRead])
def list_role_permissions(
    role_id: int,
    role_service: RoleServiceDep,
    current_user=Depends(require_permission("system:role:query")),
):
    return role_service.list_permissions(role_id)


@router.put("/{role_id}", response_model=RoleRead)
def update_role(
    request: Request,
    role_id: int,
    role_update: RoleUpdate,
    role_service: RoleServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:role:update")),
):
    item = role_service.update_item(role_id, role_update, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="role",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改角色",
        request=request,
        request_body=role_update,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.delete("/{role_id}", response_model=RoleRead)
def disable_role(
    request: Request,
    role_id: int,
    role_service: RoleServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:role:delete")),
):
    item = role_service.delete_item(role_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="role",
        resource_id=item.id,
        resource_name=item.name,
        action="delete",
        action_name="删除角色",
        request=request,
        response_params={"id": item.id, "name": item.name},
    )
    return item
