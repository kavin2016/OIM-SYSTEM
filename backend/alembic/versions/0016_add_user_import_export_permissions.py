"""Add user import and export permissions

Revision ID: 0016_user_import_export_perms
Revises: 0015_add_user_extra_fields
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_user_import_export_perms"
down_revision = "0015_add_user_extra_fields"
branch_labels = None
depends_on = None

PERMISSIONS = [
    {
        "name": "用户导入",
        "code": "system:user:import",
        "description": "导入用户数据",
        "icon": "upload",
        "sort_order": 1017,
    },
    {
        "name": "用户导出",
        "code": "system:user:export",
        "description": "导出用户数据",
        "icon": "download",
        "sort_order": 1018,
    },
]


def upgrade():
    bind = op.get_bind()
    parent_id = bind.execute(
        sa.text("SELECT id FROM permissions WHERE code = :code"),
        {"code": "system:user:list"},
    ).scalar()
    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = :code AND is_deleted = 0"),
        {"code": "admin"},
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

        if admin_role_id and permission_id:
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


def downgrade():
    bind = op.get_bind()
    codes = tuple(item["code"] for item in PERMISSIONS)
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM permissions WHERE code IN :codes"),
            {"codes": codes},
        )
    ]
    if permission_ids:
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id IN :permission_ids"),
            {"permission_ids": tuple(permission_ids)},
        )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE code IN :codes"),
        {"codes": codes},
    )
