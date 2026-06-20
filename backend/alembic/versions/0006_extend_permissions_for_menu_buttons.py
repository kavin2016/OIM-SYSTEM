"""Extend permissions for menus and buttons

Revision ID: 0006_extend_permissions
Revises: 0005_add_is_deleted
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_extend_permissions"
down_revision = "0005_add_is_deleted"
branch_labels = None
depends_on = None

PERMISSIONS = [
    {
        "name": "系统设置",
        "code": "system:settings",
        "type": "menu",
        "path": "/admin",
        "component": "Layout",
        "icon": "settings",
        "sort_order": 100,
        "description": "系统设置一级菜单",
        "children": [
            {
                "name": "用户列表",
                "code": "system:user:list",
                "type": "menu",
                "path": "/admin/users",
                "component": "AdminPanel",
                "icon": "users",
                "sort_order": 101,
                "description": "用户列表二级菜单",
                "children": [
                    ("用户查询", "system:user:query", "查询用户列表"),
                    ("用户新增", "system:user:create", "新增用户"),
                    ("用户编辑", "system:user:update", "编辑用户"),
                    ("用户删除", "system:user:delete", "删除用户"),
                ],
            },
            {
                "name": "部门列表",
                "code": "system:department:list",
                "type": "menu",
                "path": "/admin/departments",
                "component": "AdminPanel",
                "icon": "building",
                "sort_order": 102,
                "description": "部门列表二级菜单",
                "children": [
                    ("部门查询", "system:department:query", "查询部门列表"),
                    ("部门新增", "system:department:create", "新增部门"),
                    ("部门编辑", "system:department:update", "编辑部门"),
                    ("部门删除", "system:department:delete", "删除部门"),
                ],
            },
            {
                "name": "角色列表",
                "code": "system:role:list",
                "type": "menu",
                "path": "/admin/roles",
                "component": "AdminPanel",
                "icon": "shield",
                "sort_order": 103,
                "description": "角色列表二级菜单",
                "children": [
                    ("角色查询", "system:role:query", "查询角色列表"),
                    ("角色新增", "system:role:create", "新增角色"),
                    ("角色编辑", "system:role:update", "编辑角色"),
                    ("角色删除", "system:role:delete", "删除角色"),
                ],
            },
        ],
    }
]


def upgrade():
    op.add_column("permissions", sa.Column("parent_id", sa.Integer(), nullable=True, comment="父级权限ID"))
    op.add_column(
        "permissions",
        sa.Column(
            "type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'button'"),
            comment="权限类型：menu=菜单，button=按钮",
        ),
    )
    op.add_column("permissions", sa.Column("path", sa.String(length=255), nullable=True, comment="前端路由路径"))
    op.add_column("permissions", sa.Column("component", sa.String(length=255), nullable=True, comment="前端组件标识"))
    op.add_column("permissions", sa.Column("icon", sa.String(length=64), nullable=True, comment="菜单图标"))
    op.add_column(
        "permissions",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="排序值"),
    )
    op.create_index("ix_permissions_parent_id", "permissions", ["parent_id"])
    op.create_foreign_key(
        "fk_permissions_parent_id_permissions",
        "permissions",
        "permissions",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    bind = op.get_bind()
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.Integer()),
        sa.column("parent_id", sa.Integer()),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("type", sa.String()),
        sa.column("path", sa.String()),
        sa.column("component", sa.String()),
        sa.column("icon", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_deleted", sa.Boolean()),
    )

    def upsert_permission(item, parent_id=None):
        existing_id = bind.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": item["code"]},
        ).scalar()
        values = {
            "parent_id": parent_id,
            "name": item["name"],
            "code": item["code"],
            "type": item["type"],
            "path": item.get("path"),
            "component": item.get("component"),
            "icon": item.get("icon"),
            "sort_order": item["sort_order"],
            "description": item.get("description"),
            "is_active": True,
            "is_deleted": False,
        }
        if existing_id:
            bind.execute(
                permissions_table.update().where(permissions_table.c.id == existing_id).values(**values)
            )
            permission_id = existing_id
        else:
            result = bind.execute(permissions_table.insert().values(**values))
            permission_id = result.lastrowid

        for index, child in enumerate(item.get("children", []), start=1):
            if isinstance(child, tuple):
                child_item = {
                    "name": child[0],
                    "code": child[1],
                    "type": "button",
                    "path": None,
                    "component": None,
                    "icon": None,
                    "sort_order": item["sort_order"] * 10 + index,
                    "description": child[2],
                }
            else:
                child_item = child
            upsert_permission(child_item, parent_id=permission_id)

    for permission in PERMISSIONS:
        upsert_permission(permission)


def downgrade():
    bind = op.get_bind()
    codes = [
        "system:settings",
        "system:user:list",
        "system:user:query",
        "system:user:create",
        "system:user:update",
        "system:user:delete",
        "system:department:list",
        "system:department:query",
        "system:department:create",
        "system:department:update",
        "system:department:delete",
        "system:role:list",
        "system:role:query",
        "system:role:create",
        "system:role:update",
        "system:role:delete",
    ]
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})

    op.drop_constraint("fk_permissions_parent_id_permissions", "permissions", type_="foreignkey")
    op.drop_index("ix_permissions_parent_id", table_name="permissions")
    op.drop_column("permissions", "sort_order")
    op.drop_column("permissions", "icon")
    op.drop_column("permissions", "component")
    op.drop_column("permissions", "path")
    op.drop_column("permissions", "type")
    op.drop_column("permissions", "parent_id")

