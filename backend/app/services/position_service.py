from typing import Optional

from ..models.position import Position
from .base_service import ConflictError
from .named_code_service import NamedCodeService


class PositionService(NamedCodeService):
    model = Position
    resource_name = "岗位"
    name_label = "岗位名称"
    code_label = "岗位编码"

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
        name: Optional[str] = None,
        code: Optional[str] = None,
        status: Optional[int] = None,
    ):
        query = self.db.query(Position)
        if not include_deleted:
            query = query.filter(Position.is_deleted.is_(False))
        if status is not None:
            query = query.filter(Position.status == status)
        elif not include_disabled:
            query = query.filter(Position.status == 0)
        if name:
            query = query.filter(Position.name.like(f"%{name.strip()}%"))
        if code:
            query = query.filter(Position.code.like(f"%{code.strip()}%"))
        return query.order_by(
            Position.is_deleted.asc(),
            Position.sort_order.asc(),
            Position.id.desc(),
        ).offset(skip).limit(limit).all()

    def create_item(self, item_create, actor_id: int):
        self.ensure_unique(item_create.name, item_create.code)
        item = Position(
            code=item_create.code,
            name=item_create.name,
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
