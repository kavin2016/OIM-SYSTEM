from typing import List, Optional

from ..models.permission import Permission
from ..models.role import Role
from ..models.role_permission import RolePermission
from .base_service import ConflictError
from .named_code_service import NamedCodeService


class RoleService(NamedCodeService):
    model = Role
    resource_name = "角色"
    name_label = "角色名称"
    code_label = "角色编码"

    def _ensure_not_builtin_admin(self, item: Role) -> None:
        if item.code == "admin":
            raise ConflictError("系统内置 admin 角色不能修改或删除")

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
        name=None,
        code=None,
        is_active=None,
    ):
        query = self.db.query(Role)
        if not include_deleted:
            query = query.filter(Role.is_deleted.is_(False))
        if is_active is not None:
            query = query.filter(Role.is_active.is_(is_active))
        elif not include_disabled:
            query = query.filter(Role.is_active.is_(True))
        if name:
            query = query.filter(Role.name.like(f"%{name.strip()}%"))
        if code:
            query = query.filter(Role.code.like(f"%{code.strip()}%"))
        return query.order_by(Role.sort_order.asc(), Role.id.desc()).offset(skip).limit(limit).all()

    def _normalize_permission_ids(self, permission_ids: Optional[List[int]]) -> List[int]:
        if not permission_ids:
            return []
        normalized: List[int] = []
        for permission_id in permission_ids:
            if isinstance(permission_id, int) and permission_id > 0 and permission_id not in normalized:
                normalized.append(permission_id)
        return normalized

    def _ensure_permissions_exist(self, permission_ids: List[int]) -> None:
        if not permission_ids:
            return
        found_ids = {
            item.id
            for item in self.db.query(Permission.id)
            .filter(
                Permission.id.in_(permission_ids),
                Permission.is_deleted.is_(False),
            )
            .all()
        }
        missing_ids = [permission_id for permission_id in permission_ids if permission_id not in found_ids]
        if missing_ids:
            raise ConflictError("选择的菜单权限不存在或已删除")

    def replace_permissions(self, role_id: int, permission_ids: Optional[List[int]]) -> None:
        normalized_ids = self._normalize_permission_ids(permission_ids)
        self._ensure_permissions_exist(normalized_ids)
        self.db.query(RolePermission).filter(RolePermission.role_id == role_id).delete(synchronize_session=False)
        for permission_id in normalized_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=permission_id))

    def create_item(self, item_create, actor_id: int):
        self.ensure_unique(item_create.name, item_create.code)
        item = Role(
            name=item_create.name,
            code=item_create.code,
            sort_order=item_create.sort_order,
            description=item_create.description,
            is_active=item_create.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.db.add(item)
        try:
            self.db.flush()
            self.replace_permissions(item.id, item_create.permission_ids)
            self.db.commit()
        except ConflictError:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise ConflictError(f"{self.name_label}或{self.code_label}已存在") from exc
        self.db.refresh(item)
        return item

    def update_item(self, item_id: int, item_update, actor_id: int):
        item = self.get_required(item_id)
        self._ensure_not_builtin_admin(item)
        self.ensure_unique(item_update.name, item_update.code, current_id=item.id)

        update_data = item_update.model_dump(exclude_unset=True, exclude={"permission_ids"})
        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        item.updated_by = actor_id
        try:
            if "permission_ids" in item_update.model_fields_set:
                self.replace_permissions(item.id, item_update.permission_ids)
            self.db.add(item)
            self.db.commit()
        except ConflictError:
            self.db.rollback()
            raise
        except Exception as exc:
            self.db.rollback()
            raise ConflictError(f"{self.name_label}或{self.code_label}已存在") from exc
        self.db.refresh(item)
        return item

    def delete_item(self, item_id: int, actor_id: int):
        item = self.get_required(item_id)
        self._ensure_not_builtin_admin(item)
        item.is_deleted = True
        item.is_active = False
        item.updated_by = actor_id
        return self.commit(item, f"{self.resource_name}删除失败")

    def list_permissions(self, role_id: int) -> List[Permission]:
        self.get_required(role_id)
        checked_permission_ids = {
            item.permission_id
            for item in self.db.query(RolePermission.permission_id)
            .filter(RolePermission.role_id == role_id)
            .all()
        }
        permissions = (
            self.db.query(Permission)
            .filter(
                Permission.is_active.is_(True),
                Permission.is_deleted.is_(False),
            )
            .order_by(Permission.sort_order.asc(), Permission.id.asc())
            .all()
        )
        for permission in permissions:
            permission.checked = permission.id in checked_permission_ids
        return permissions
