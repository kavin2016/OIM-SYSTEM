"""Group OpenVPN menus under parent menu

Revision ID: 0030_group_openvpn_menus
Revises: 0029_openvpn_split_components
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import bindparam


revision = "0030_group_openvpn_menus"
down_revision = "0029_openvpn_split_components"
branch_labels = None
depends_on = None


OPENVPN_PARENT_CODE = "ops:openvpn:list"
OPENVPN_CHILD_CODES = [
    "ops:openvpn:server:list",
    "ops:openvpn:account:list",
    "ops:openvpn:session:list",
    "ops:openvpn:log:list",
    "ops:openvpn:rule:list",
]

OPENVPN_CHILD_SORTS = {
    "ops:openvpn:server:list": 1,
    "ops:openvpn:account:list": 2,
    "ops:openvpn:session:list": 3,
    "ops:openvpn:log:list": 4,
    "ops:openvpn:rule:list": 5,
}


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM sys_permissions WHERE code = :code"), {"code": code}).scalar()


def _ensure_openvpn_parent(bind):
    ops_id = _permission_id(bind, "ops")
    parent_id = _permission_id(bind, OPENVPN_PARENT_CODE)
    values = {
        "parent_id": ops_id,
        "name": "OpenVPN管理",
        "code": OPENVPN_PARENT_CODE,
        "type": "menu",
        "path": "/ops/openvpn",
        "component": None,
        "icon": "connection",
        "sort_order": 301,
        "description": "OpenVPN管理",
        "is_active": True,
        "is_deleted": False,
    }

    if parent_id:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
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
            {**values, "id": parent_id},
        )
        return parent_id

    result = bind.execute(
        sa.text(
            """
            INSERT INTO sys_permissions
                (parent_id, name, code, type, path, component, icon, sort_order, description, is_active, is_deleted)
            VALUES
                (:parent_id, :name, :code, :type, :path, :component, :icon, :sort_order, :description, :is_active, :is_deleted)
            """
        ),
        values,
    )
    return result.lastrowid


def _grant_parent_to_roles(bind, parent_id):
    child_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM sys_permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
            {"codes": tuple(OPENVPN_CHILD_CODES)},
        )
    ]
    if not child_ids:
        return

    bind.execute(
        sa.text(
            """
            INSERT INTO sys_role_permissions (role_id, permission_id, created_at)
            SELECT DISTINCT rp.role_id, :parent_id, CURRENT_TIMESTAMP
            FROM sys_role_permissions rp
            WHERE rp.permission_id IN :child_ids
              AND NOT EXISTS (
                SELECT 1
                FROM sys_role_permissions existing
                WHERE existing.role_id = rp.role_id
                  AND existing.permission_id = :parent_id
              )
            """
        ).bindparams(bindparam("child_ids", expanding=True)),
        {"parent_id": parent_id, "child_ids": tuple(child_ids)},
    )


def upgrade():
    bind = op.get_bind()
    parent_id = _ensure_openvpn_parent(bind)

    for code in OPENVPN_CHILD_CODES:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
                SET parent_id = :parent_id,
                    sort_order = :sort_order,
                    is_active = 1,
                    is_deleted = 0
                WHERE code = :code
                """
            ),
            {"parent_id": parent_id, "sort_order": OPENVPN_CHILD_SORTS[code], "code": code},
        )

    _grant_parent_to_roles(bind, parent_id)


def downgrade():
    bind = op.get_bind()
    ops_id = _permission_id(bind, "ops")
    parent_id = _permission_id(bind, OPENVPN_PARENT_CODE)

    for index, code in enumerate(OPENVPN_CHILD_CODES, start=301):
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
                SET parent_id = :parent_id,
                    sort_order = :sort_order
                WHERE code = :code
                """
            ),
            {"parent_id": ops_id, "sort_order": index, "code": code},
        )

    if parent_id:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
                SET is_active = 0,
                    path = NULL,
                    component = NULL
                WHERE id = :id
                """
            ),
            {"id": parent_id},
        )
