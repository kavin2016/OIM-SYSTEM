from typing import Optional

from fastapi import APIRouter, Depends, status

from ..dependencies import DepartmentServiceDep
from ..schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from ..security import require_permission

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    department_service: DepartmentServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    name: Optional[str] = None,
    code: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user=Depends(require_permission("system:department:query")),
):
    return department_service.list(
        skip=skip,
        limit=limit,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
        name=name,
        code=code,
        is_active=is_active,
    )


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    department_create: DepartmentCreate,
    department_service: DepartmentServiceDep,
    current_user=Depends(require_permission("system:department:create")),
):
    return department_service.create_item(department_create, actor_id=current_user.id)


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int,
    department_service: DepartmentServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:department:query")),
):
    return department_service.get_required(department_id, include_deleted=include_deleted)


@router.put("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    department_update: DepartmentUpdate,
    department_service: DepartmentServiceDep,
    current_user=Depends(require_permission("system:department:update")),
):
    return department_service.update_item(department_id, department_update, actor_id=current_user.id)


@router.delete("/{department_id}", response_model=DepartmentRead)
def disable_department(
    department_id: int,
    department_service: DepartmentServiceDep,
    current_user=Depends(require_permission("system:department:delete")),
):
    return department_service.delete_item(department_id, actor_id=current_user.id)
