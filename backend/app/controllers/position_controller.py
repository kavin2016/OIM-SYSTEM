from typing import Optional

from fastapi import APIRouter, Depends, status

from ..dependencies import PositionServiceDep
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
    position_create: PositionCreate,
    position_service: PositionServiceDep,
    current_user=Depends(require_permission("system:position:create")),
):
    return position_service.create_item(position_create, actor_id=current_user.id)


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
    position_id: int,
    position_update: PositionUpdate,
    position_service: PositionServiceDep,
    current_user=Depends(require_permission("system:position:update")),
):
    return position_service.update_item(position_id, position_update, actor_id=current_user.id)


@router.delete("/{position_id}", response_model=PositionRead)
def disable_position(
    position_id: int,
    position_service: PositionServiceDep,
    current_user=Depends(require_permission("system:position:delete")),
):
    return position_service.delete_item(position_id, actor_id=current_user.id)
