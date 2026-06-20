"""Prefix system configuration tables with sys

Revision ID: 0027_prefix_system_tables
Revises: 0026_add_openvpn_management
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_prefix_system_tables"
down_revision = "0026_add_openvpn_management"
branch_labels = None
depends_on = None


TABLE_RENAMES = (
    ("users", "sys_users"),
    ("departments", "sys_departments"),
    ("roles", "sys_roles"),
    ("permissions", "sys_permissions"),
    ("positions", "sys_positions"),
    ("domains", "sys_domains"),
    ("user_departments", "sys_user_departments"),
    ("user_roles", "sys_user_roles"),
    ("user_positions", "sys_user_positions"),
    ("role_permissions", "sys_role_permissions"),
)


def _table_exists(bind, table_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _rename_table_if_needed(bind, old_name: str, new_name: str) -> None:
    old_exists = _table_exists(bind, old_name)
    new_exists = _table_exists(bind, new_name)
    if old_exists and not new_exists:
        op.rename_table(old_name, new_name)
    elif old_exists and new_exists:
        raise RuntimeError(f"Both {old_name} and {new_name} exist; please merge data before running this migration")


def upgrade():
    bind = op.get_bind()
    for old_name, new_name in TABLE_RENAMES:
        _rename_table_if_needed(bind, old_name, new_name)


def downgrade():
    bind = op.get_bind()
    for old_name, new_name in reversed(TABLE_RENAMES):
        _rename_table_if_needed(bind, new_name, old_name)
