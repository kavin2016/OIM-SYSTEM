from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, status

from ..dependencies import UserServiceDep
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

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user=Depends(get_current_active_user)):
    return current_user


@router.put("/me", response_model=UserRead)
def update_current_user(
    user_update: UserUpdate,
    user_service: UserServiceDep,
    current_user=Depends(get_current_active_user),
):
    return user_service.update_user(current_user, user_update, actor_id=current_user.id)


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
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    user_create: UserAdminCreate,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:create")),
):
    return user_service.create_admin_user(user_create, actor_id=current_user.id)


@router.post("/batch-delete", response_model=list[UserRead])
def batch_delete_users(
    payload: UserBatchDelete,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:delete")),
):
    return user_service.delete_users(payload.user_ids, actor_id=current_user.id)


@router.post("/{user_id}/reset-password", response_model=UserRead)
def reset_user_password(
    user_id: int,
    payload: UserResetPassword,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:reset-password")),
):
    return user_service.reset_password(user_id, payload.password, actor_id=current_user.id)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    user_service: UserServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:user:query")),
):
    return user_service.get_required(user_id, include_deleted=include_deleted)


@router.get("/{user_id}/departments", response_model=list[DepartmentRead])
def list_user_departments(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:query")),
):
    return user_service.list_departments(user_id)


@router.get("/{user_id}/roles", response_model=list[RoleRead])
def list_user_roles(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:assign-role")),
):
    return user_service.list_roles(user_id)


@router.get("/{user_id}/positions", response_model=list[PositionRead])
def list_user_positions(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:query")),
):
    return user_service.list_positions(user_id)


@router.put("/{user_id}/roles", response_model=UserRead)
def assign_user_roles(
    user_id: int,
    payload: UserAssignRoles,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:assign-role")),
):
    return user_service.assign_roles(user_id, payload.role_ids, actor_id=current_user.id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    user_update: UserAdminUpdate,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:update")),
):
    return user_service.update_admin_user(user_id, user_update, actor_id=current_user.id)


@router.delete("/{user_id}", response_model=UserRead)
def disable_user(
    user_id: int,
    user_service: UserServiceDep,
    current_user=Depends(require_permission("system:user:delete")),
):
    return user_service.delete_user(user_id, actor_id=current_user.id)
