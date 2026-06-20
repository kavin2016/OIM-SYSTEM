from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, status

from ..dependencies import DomainServiceDep
from ..schemas.domain import DomainCreate, DomainRead, DomainUpdate
from ..security import require_permission

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[DomainRead])
def list_domains(
    domain_service: DomainServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    name: Optional[str] = None,
    code: Optional[str] = None,
    status: Optional[int] = None,
    registrar: Optional[str] = None,
    expiring_before: Optional[date] = None,
    current_user=Depends(require_permission("system:domain:query")),
):
    return domain_service.list(
        skip=skip,
        limit=limit,
        include_disabled=include_disabled,
        include_deleted=include_deleted,
        name=name,
        code=code,
        status=status,
        registrar=registrar,
        expiring_before=expiring_before,
    )


@router.post("", response_model=DomainRead, status_code=status.HTTP_201_CREATED)
def create_domain(
    domain_create: DomainCreate,
    domain_service: DomainServiceDep,
    current_user=Depends(require_permission("system:domain:create")),
):
    return domain_service.create_item(domain_create, actor_id=current_user.id)


@router.get("/{domain_id}", response_model=DomainRead)
def get_domain(
    domain_id: int,
    domain_service: DomainServiceDep,
    include_deleted: bool = False,
    current_user=Depends(require_permission("system:domain:query")),
):
    return domain_service.get_required(domain_id, include_deleted=include_deleted)


@router.put("/{domain_id}", response_model=DomainRead)
def update_domain(
    domain_id: int,
    domain_update: DomainUpdate,
    domain_service: DomainServiceDep,
    current_user=Depends(require_permission("system:domain:update")),
):
    return domain_service.update_item(domain_id, domain_update, actor_id=current_user.id)


@router.delete("/{domain_id}", response_model=DomainRead)
def disable_domain(
    domain_id: int,
    domain_service: DomainServiceDep,
    current_user=Depends(require_permission("system:domain:delete")),
):
    return domain_service.delete_item(domain_id, actor_id=current_user.id)
