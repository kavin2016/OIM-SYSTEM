"""Add position menu and user positions

Revision ID: 0019_position_user_rel
Revises: 0018_create_positions
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0019_position_user_rel"
down_revision = "0018_create_positions"
branch_labels = None
depends_on = None

POSITION_PERMISSIONS = [
    {
        "name": "岗位管理",
        "code": "system:position:list",
        "type": "menu",
        "path": "/admin/positions",
        "component": "PositionList",
        "icon": "briefcase",
        "sort_order": 104,
        "description": "岗位管理二级菜单",
        "children": [
            ("岗位查询", "system:position:query", "查询岗位列表"),
            ("岗位新增", "system:position:create", "新增岗位"),
            ("岗位修改", "system:position:update", "修改岗位"),
            ("岗位删除", "system:position:delete", "删除岗位"),
        ],
    }
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).scalar()


def _upsert_permission(bind, item, parent_id=None):
    existing_id = _permission_id(bind, item["code"])
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
            sa.text(
                """
                UPDATE permissions
                SET parent_id = :parent_id,
                    name = :name,
                    type = :type,
                    path = :path,
                    component = :component,
                    icon = :icon,
                    sort_order = :sort_order,
                    description = :description,
                    is_active = :is_active,
                    is_deleted = :is_deleted
                WHERE id = :id
                """
            ),
            {**values, "id": existing_id},
        )
        permission_id = existing_id
    else:
        result = bind.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (parent_id, name, code, type, path, component, icon, sort_order, description, is_active, is_deleted)
                VALUES
                    (:parent_id, :name, :code, :type, :path, :component, :icon, :sort_order, :description, :is_active, :is_deleted)
                """
            ),
            values,
        )
        permission_id = result.lastrowid

    for index, child in enumerate(item.get("children", []), start=1):
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
        _upsert_permission(bind, child_item, permission_id)

    return permission_id


def _grant_to_admin_role(bind, codes):
    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = :code AND is_deleted = 0"),
        {"code": "admin"},
    ).scalar()
    if not admin_role_id:
        return
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM permissions WHERE code IN :codes"),
            {"codes": tuple(codes)},
        )
    ]
    for permission_id in permission_ids:
        exists = bind.execute(
            sa.text(
                """
                SELECT id FROM role_permissions
                WHERE role_id = :role_id AND permission_id = :permission_id
                """
            ),
            {"role_id": admin_role_id, "permission_id": permission_id},
        ).scalar()
        if not exists:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id, created_at)
                    VALUES (:role_id, :permission_id, CURRENT_TIMESTAMP)
                    """
                ),
                {"role_id": admin_role_id, "permission_id": permission_id},
            )


def upgrade():
    op.create_table(
        "user_positions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="用户岗位关系ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("position_id", sa.Integer(), nullable=False, comment="岗位ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "position_id", name="uq_user_positions_user_position"),
    )
    op.create_index("ix_user_positions_id", "user_positions", ["id"])
    op.create_index("ix_user_positions_user_id", "user_positions", ["user_id"])
    op.create_index("ix_user_positions_position_id", "user_positions", ["position_id"])

    bind = op.get_bind()
    system_parent_id = _permission_id(bind, "system:settings")
    all_codes = []
    for permission in POSITION_PERMISSIONS:
        _upsert_permission(bind, permission, system_parent_id)
        all_codes.append(permission["code"])
        all_codes.extend(child[1] for child in permission["children"])
    _grant_to_admin_role(bind, all_codes)


def downgrade():
    bind = op.get_bind()
    codes = ["system:position:list", "system:position:query", "system:position:create", "system:position:update", "system:position:delete"]
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM permissions WHERE code IN :codes"),
            {"codes": tuple(codes)},
        )
    ]
    if permission_ids:
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id IN :permission_ids"),
            {"permission_ids": tuple(permission_ids)},
        )
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})

    op.drop_index("ix_user_positions_position_id", table_name="user_positions")
    op.drop_index("ix_user_positions_user_id", table_name="user_positions")
    op.drop_index("ix_user_positions_id", table_name="user_positions")
    op.drop_table("user_positions")
