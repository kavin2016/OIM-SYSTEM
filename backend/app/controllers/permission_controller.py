from fastapi import APIRouter, Depends, Request, status

from ..dependencies import OperationLogServiceDep, PermissionServiceDep
from ..schemas.permission import PermissionCreate, PermissionRead, PermissionUpdate
from ..security import require_permission

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=list[PermissionRead])
def list_permissions(
    permission_service: PermissionServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:role:query")),
):
    return permission_service.list(
        skip=skip,
        limit=limit,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
    )


@router.post("", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
def create_permission(
    request: Request,
    permission_create: PermissionCreate,
    permission_service: PermissionServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:role:create")),
):
    item = permission_service.create_item(permission_create, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="permission",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增权限",
        request=request,
        request_body=permission_create,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "code": item.code},
    )
    return item


@router.get("/{permission_id}", response_model=PermissionRead)
def get_permission(
    permission_id: int,
    permission_service: PermissionServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:role:query")),
):
    return permission_service.get_required(permission_id, include_deleted=include_deleted)


@router.put("/{permission_id}", response_model=PermissionRead)
def update_permission(
    request: Request,
    permission_id: int,
    permission_update: PermissionUpdate,
    permission_service: PermissionServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:role:update")),
):
    item = permission_service.update_item(permission_id, permission_update, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="permission",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改权限",
        request=request,
        request_body=permission_update,
        response_params={"id": item.id, "code": item.code},
    )
    return item


@router.delete("/{permission_id}", response_model=PermissionRead)
def disable_permission(
    request: Request,
    permission_id: int,
    permission_service: PermissionServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:role:delete")),
):
    item = permission_service.delete_item(permission_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="permission",
        resource_id=item.id,
        resource_name=item.name,
        action="delete",
        action_name="删除权限",
        request=request,
        response_params={"id": item.id, "code": item.code},
    )
    return item
