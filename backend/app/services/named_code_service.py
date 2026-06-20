from typing import Optional

from .base_service import BaseService, ConflictError


class NamedCodeService(BaseService):
    name_label = "名称"
    code_label = "编码"

    def get_by_name(self, name: str):
        return self.db.query(self.model).filter(self.model.name == name, self.model.is_deleted.is_(False)).first()

    def get_by_code(self, code: str):
        return self.db.query(self.model).filter(self.model.code == code, self.model.is_deleted.is_(False)).first()

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
        name: Optional[str] = None,
        code: Optional[str] = None,
        is_active: Optional[bool] = None,
    ):
        query = self.db.query(self.model)
        if not include_deleted:
            query = query.filter(self.model.is_deleted.is_(False))
        if is_active is not None:
            query = query.filter(self.model.is_active.is_(is_active))
        elif not include_disabled:
            query = query.filter(self.model.is_active.is_(True))
        if name:
            query = query.filter(self.model.name.like(f"%{name.strip()}%"))
        if code:
            query = query.filter(self.model.code.like(f"%{code.strip()}%"))
        return query.order_by(self.model.id.desc()).offset(skip).limit(limit).all()

    def ensure_unique(self, name: Optional[str], code: Optional[str], current_id: int = None) -> None:
        if name is not None:
            existing = self.get_by_name(name)
            if existing and existing.id != current_id:
                raise ConflictError(f"{self.name_label}已存在")
        if code is not None:
            existing = self.get_by_code(code)
            if existing and existing.id != current_id:
                raise ConflictError(f"{self.code_label}已存在")

    def create_item(self, item_create, actor_id: int):
        self.ensure_unique(item_create.name, item_create.code)
        item = self.model(
            name=item_create.name,
            code=item_create.code,
            description=item_create.description,
            is_active=item_create.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self.commit(item, f"{self.name_label}或{self.code_label}已存在")

    def update_item(self, item_id: int, item_update, actor_id: int):
        item = self.get_required(item_id)
        self.ensure_unique(item_update.name, item_update.code, current_id=item.id)

        update_data = item_update.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        item.updated_by = actor_id
        return self.commit(item, f"{self.name_label}或{self.code_label}已存在")

    def delete_item(self, item_id: int, actor_id: int):
        item = self.get_required(item_id)
        item.is_deleted = True
        item.is_active = False
        item.updated_by = actor_id
        return self.commit(item, f"{self.resource_name}删除失败")
