from typing import Optional

from fastapi import APIRouter, Depends, status

from ..dependencies import RoleServiceDep
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
    role_create: RoleCreate,
    role_service: RoleServiceDep,
    current_user=Depends(require_permission("system:role:create")),
):
    return role_service.create_item(role_create, actor_id=current_user.id)


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
    role_id: int,
    role_update: RoleUpdate,
    role_service: RoleServiceDep,
    current_user=Depends(require_permission("system:role:update")),
):
    return role_service.update_item(role_id, role_update, actor_id=current_user.id)


@router.delete("/{role_id}", response_model=RoleRead)
def disable_role(
    role_id: int,
    role_service: RoleServiceDep,
    current_user=Depends(require_permission("system:role:delete")),
):
    return role_service.delete_item(role_id, actor_id=current_user.id)
