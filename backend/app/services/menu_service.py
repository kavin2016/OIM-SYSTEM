from sqlalchemy.orm import Session

from ..models.permission import Permission
from ..models.role import Role
from ..models.role_permission import RolePermission
from ..models.user import User
from ..models.user_role import UserRole


class MenuService:
    def __init__(self, db: Session):
        self.db = db

    def list_user_access(self, user: User) -> dict:
        query = self.db.query(Permission).filter(
            Permission.is_active.is_(True),
            Permission.is_deleted.is_(False),
        )

        if not user.is_admin:
            query = (
                query.join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
                .filter(
                    UserRole.user_id == user.id,
                    Role.is_active.is_(True),
                    Role.is_deleted.is_(False),
                )
                .distinct()
            )

        permissions = query.order_by(Permission.sort_order.asc(), Permission.id.asc()).all()
        menus = [permission for permission in permissions if permission.type == "menu"]
        return {
            "menus": self._build_tree(menus),
            "permissions": sorted({permission.code for permission in permissions}),
        }

    def list_user_menus(self, user: User) -> list[dict]:
        query = self.db.query(Permission).filter(
            Permission.type == "menu",
            Permission.is_active.is_(True),
            Permission.is_deleted.is_(False),
        )

        if not user.is_admin:
            query = (
                query.join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
                .filter(
                    UserRole.user_id == user.id,
                    Role.is_active.is_(True),
                    Role.is_deleted.is_(False),
                )
                .distinct()
            )

        menus = query.order_by(Permission.sort_order.asc(), Permission.id.asc()).all()
        return self._build_tree(menus)

    def list_user_permission_codes(self, user: User) -> list[str]:
        query = self.db.query(Permission.code).filter(
            Permission.is_active.is_(True),
            Permission.is_deleted.is_(False),
        )

        if not user.is_admin:
            query = (
                query.join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
                .filter(
                    UserRole.user_id == user.id,
                    Role.is_active.is_(True),
                    Role.is_deleted.is_(False),
                )
                .distinct()
            )

        return [row.code for row in query.order_by(Permission.code.asc()).all()]

    def _build_tree(self, menus: list[Permission]) -> list[dict]:
        items_by_id = {
            menu.id: {
                "id": menu.id,
                "parent_id": menu.parent_id,
                "name": menu.name,
                "code": menu.code,
                "path": menu.path,
                "component": menu.component,
                "icon": menu.icon,
                "sort_order": menu.sort_order,
                "children": [],
            }
            for menu in menus
        }

        roots = []
        for item in items_by_id.values():
            parent = items_by_id.get(item["parent_id"])
            if parent:
                parent["children"].append(item)
            else:
                roots.append(item)

        return roots
