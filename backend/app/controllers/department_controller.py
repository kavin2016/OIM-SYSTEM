from typing import Optional

from fastapi import APIRouter, Depends, Request, status

from ..dependencies import DepartmentServiceDep, OperationLogServiceDep
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
    request: Request,
    department_create: DepartmentCreate,
    department_service: DepartmentServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:department:create")),
):
    item = department_service.create_item(department_create, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="department",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增部门",
        request=request,
        request_body=department_create,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "name": item.name},
    )
    return item


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
    request: Request,
    department_id: int,
    department_update: DepartmentUpdate,
    department_service: DepartmentServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:department:update")),
):
    item = department_service.update_item(department_id, department_update, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="department",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改部门",
        request=request,
        request_body=department_update,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.delete("/{department_id}", response_model=DepartmentRead)
def disable_department(
    request: Request,
    department_id: int,
    department_service: DepartmentServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:department:delete")),
):
    item = department_service.delete_item(department_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="department",
        resource_id=item.id,
        resource_name=item.name,
        action="delete",
        action_name="删除部门",
        request=request,
        response_params={"id": item.id, "name": item.name},
    )
    return item
