"""Add OpenVPN account revoke permission

Revision ID: 0032_openvpn_account_revoke
Revises: 0031_openvpn_ssh_easyrsa
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import bindparam


revision = "0032_openvpn_account_revoke"
down_revision = "0031_openvpn_ssh_easyrsa"
branch_labels = None
depends_on = None


PERMISSION_CODE = "ops:openvpn:account:revoke"
PARENT_CODE = "ops:openvpn:account:list"


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM sys_permissions WHERE code = :code"), {"code": code}).scalar()


def upgrade():
    bind = op.get_bind()
    parent_id = _permission_id(bind, PARENT_CODE)
    permission_id = _permission_id(bind, PERMISSION_CODE)
    values = {
        "parent_id": parent_id,
        "name": "账号吊销",
        "code": PERMISSION_CODE,
        "type": "button",
        "path": None,
        "component": None,
        "icon": None,
        "sort_order": 36,
        "description": "吊销OpenVPN账号",
        "is_active": True,
        "is_deleted": False,
    }
    if permission_id:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
                SET parent_id = :parent_id,
                    name = :name,
                    type = :type,
                    sort_order = :sort_order,
                    description = :description,
                    is_active = :is_active,
                    is_deleted = :is_deleted
                WHERE id = :id
                """
            ),
            {**values, "id": permission_id},
        )
    else:
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
        permission_id = result.lastrowid

    source_ids = [
        item
        for item in (
            _permission_id(bind, "ops:openvpn:account:disable"),
            _permission_id(bind, "ops:openvpn:cert:revoke"),
        )
        if item
    ]
    if permission_id and source_ids:
        statement = sa.text(
            """
            INSERT INTO sys_role_permissions (role_id, permission_id, created_at)
            SELECT DISTINCT rp.role_id, :permission_id, CURRENT_TIMESTAMP
            FROM sys_role_permissions rp
            WHERE rp.permission_id IN :source_ids
              AND NOT EXISTS (
                SELECT 1
                FROM sys_role_permissions existing
                WHERE existing.role_id = rp.role_id
                  AND existing.permission_id = :permission_id
              )
            """
        ).bindparams(bindparam("source_ids", expanding=True))
        bind.execute(statement, {"permission_id": permission_id, "source_ids": tuple(source_ids)})


def downgrade():
    bind = op.get_bind()
    permission_id = _permission_id(bind, PERMISSION_CODE)
    if not permission_id:
        return
    bind.execute(sa.text("DELETE FROM sys_role_permissions WHERE permission_id = :id"), {"id": permission_id})
    bind.execute(sa.text("DELETE FROM sys_permissions WHERE id = :id"), {"id": permission_id})
