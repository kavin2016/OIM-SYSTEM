from fastapi import APIRouter, Depends, status

from ..dependencies import PermissionServiceDep
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
    permission_create: PermissionCreate,
    permission_service: PermissionServiceDep,
    current_user=Depends(require_permission("system:role:create")),
):
    return permission_service.create_item(permission_create, actor_id=current_user.id)


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
    permission_id: int,
    permission_update: PermissionUpdate,
    permission_service: PermissionServiceDep,
    current_user=Depends(require_permission("system:role:update")),
):
    return permission_service.update_item(permission_id, permission_update, actor_id=current_user.id)


@router.delete("/{permission_id}", response_model=PermissionRead)
def disable_permission(
    permission_id: int,
    permission_service: PermissionServiceDep,
    current_user=Depends(require_permission("system:role:delete")),
):
    return permission_service.delete_item(permission_id, actor_id=current_user.id)
