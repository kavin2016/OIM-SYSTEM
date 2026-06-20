"""Add user action permissions

Revision ID: 0011_add_user_action_permissions
Revises: 0010_rename_system_menu_labels
Create Date: 2026-06-10 20:12:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_add_user_action_permissions"
down_revision = "0010_rename_system_menu_labels"
branch_labels = None
depends_on = None

PERMISSIONS = [
    {
        "name": "用户重置密码",
        "code": "system:user:reset-password",
        "description": "重置用户密码",
        "icon": "key",
        "sort_order": 1015,
    },
    {
        "name": "用户分配角色",
        "code": "system:user:assign-role",
        "description": "分配用户角色",
        "icon": "shield",
        "sort_order": 1016,
    },
]


def upgrade():
    bind = op.get_bind()
    parent_id = bind.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": "system:user:list"},
    ).scalar()

    for item in PERMISSIONS:
        existing_id = bind.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": item["code"]},
        ).scalar()
        values = {
            "parent_id": parent_id,
            "name": item["name"],
            "code": item["code"],
            "type": "button",
            "path": None,
            "component": None,
            "icon": item["icon"],
            "sort_order": item["sort_order"],
            "description": item["description"],
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
        else:
            bind.execute(
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


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM permissions WHERE code IN :codes"),
        {"codes": tuple(item["code"] for item in PERMISSIONS)},
    )
