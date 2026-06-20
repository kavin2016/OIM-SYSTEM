from datetime import date
from typing import Optional

from ..models.domain import Domain
from .named_code_service import NamedCodeService


class DomainService(NamedCodeService):
    model = Domain
    resource_name = "域名"
    name_label = "域名名称"
    code_label = "域名地址"

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
        name: Optional[str] = None,
        code: Optional[str] = None,
        status: Optional[int] = None,
        registrar: Optional[str] = None,
        expiring_before: Optional[date] = None,
    ):
        query = self.db.query(Domain)
        if not include_deleted:
            query = query.filter(Domain.is_deleted.is_(False))
        if status is not None:
            query = query.filter(Domain.status == status)
        elif not include_disabled:
            query = query.filter(Domain.status == 0)
        if name:
            query = query.filter(Domain.name.like(f"%{name.strip()}%"))
        if code:
            query = query.filter(Domain.code.like(f"%{code.strip()}%"))
        if registrar:
            query = query.filter(Domain.registrar.like(f"%{registrar.strip()}%"))
        if expiring_before:
            query = query.filter(Domain.expiry_date.isnot(None), Domain.expiry_date <= expiring_before)
        return query.order_by(Domain.sort_order.asc(), Domain.id.desc()).offset(skip).limit(limit).all()

    def create_item(self, item_create, actor_id: int):
        self.ensure_unique(item_create.name, item_create.code)
        item = Domain(
            code=item_create.code,
            name=item_create.name,
            registrar=item_create.registrar,
            expiry_date=item_create.expiry_date,
            sort_order=item_create.sort_order,
            status=item_create.status,
            remark=item_create.remark,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self.commit(item, f"{self.name_label}或{self.code_label}已存在")

    def update_item(self, item_id: int, item_update, actor_id: int):
        item = self.get_required(item_id, include_deleted=True)
        self.ensure_unique(item_update.name, item_update.code, current_id=item.id)
        update_data = item_update.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        if item.is_deleted:
            item.status = 1
        item.updated_by = actor_id
        return self.commit(item, f"{self.name_label}或{self.code_label}已存在")

    def delete_item(self, item_id: int, actor_id: int):
        item = self.get_required(item_id)
        item.is_deleted = True
        item.status = 1
        item.updated_by = actor_id
        return self.commit(item, f"{self.resource_name}删除失败")
