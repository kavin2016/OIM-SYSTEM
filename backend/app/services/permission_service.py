from ..models.permission import Permission
from .named_code_service import NamedCodeService


class PermissionService(NamedCodeService):
    model = Permission
    resource_name = "权限"
    name_label = "权限名称"
    code_label = "权限编码"

    def create_item(self, item_create, actor_id: int):
        self.ensure_unique(item_create.name, item_create.code)
        item = Permission(
            parent_id=item_create.parent_id,
            name=item_create.name,
            code=item_create.code,
            type=item_create.type,
            path=item_create.path,
            component=item_create.component,
            icon=item_create.icon,
            sort_order=item_create.sort_order,
            description=item_create.description,
            is_active=item_create.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self.commit(item, "权限名称或权限编码已存在")

    def update_item(self, item_id: int, item_update, actor_id: int):
        item = self.get_required(item_id)
        self.ensure_unique(item_update.name, item_update.code, current_id=item.id)

        update_data = item_update.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        item.updated_by = actor_id
        return self.commit(item, "权限名称或权限编码已存在")
