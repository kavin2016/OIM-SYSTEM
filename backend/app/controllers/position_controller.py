from typing import Optional

from fastapi import APIRouter, Depends, Request, status

from ..dependencies import OperationLogServiceDep, PositionServiceDep
from ..schemas.position import PositionCreate, PositionRead, PositionUpdate
from ..security import require_permission

router = APIRouter(prefix="/positions", tags=["positions"])


@router.get("", response_model=list[PositionRead])
def list_positions(
    position_service: PositionServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    name: Optional[str] = None,
    code: Optional[str] = None,
    status: Optional[int] = None,
    current_user=Depends(require_permission("system:position:query")),
):
    return position_service.list(
        skip=skip,
        limit=limit,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
        name=name,
        code=code,
        status=status,
    )


@router.post("", response_model=PositionRead, status_code=status.HTTP_201_CREATED)
def create_position(
    request: Request,
    position_create: PositionCreate,
    position_service: PositionServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:position:create")),
):
    item = position_service.create_item(position_create, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="position",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增岗位",
        request=request,
        request_body=position_create,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.get("/{position_id}", response_model=PositionRead)
def get_position(
    position_id: int,
    position_service: PositionServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:position:query")),
):
    return position_service.get_required(position_id, include_deleted=include_deleted)


@router.put("/{position_id}", response_model=PositionRead)
def update_position(
    request: Request,
    position_id: int,
    position_update: PositionUpdate,
    position_service: PositionServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:position:update")),
):
    item = position_service.update_item(position_id, position_update, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="position",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改岗位",
        request=request,
        request_body=position_update,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.delete("/{position_id}", response_model=PositionRead)
def disable_position(
    request: Request,
    position_id: int,
    position_service: PositionServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("system:position:delete")),
):
    item = position_service.delete_item(position_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="system",
        module_name="系统管理",
        resource_type="position",
        resource_id=item.id,
        resource_name=item.name,
        action="delete",
        action_name="删除岗位",
        request=request,
        response_params={"id": item.id, "name": item.name},
    )
    return item
