"""Enforce single user role and department

Revision ID: 0040_single_user_scope
Revises: 0039_user_data_scope
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0040_single_user_scope"
down_revision = "0039_user_data_scope"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _constraint_exists(bind, table_name: str, constraint_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                  AND CONSTRAINT_NAME = :constraint_name
                """
            ),
            {"table_name": table_name, "constraint_name": constraint_name},
        ).scalar()
    )


def _delete_duplicate_user_rows(bind, table_name: str) -> None:
    bind.execute(
        sa.text(
            f"""
            DELETE target
            FROM {table_name} AS target
            INNER JOIN {table_name} AS kept
              ON target.user_id = kept.user_id
             AND target.id > kept.id
            """
        )
    )


def _create_unique_user_constraint(table_name: str, constraint_name: str) -> None:
    bind = op.get_bind()
    if _table_exists(bind, table_name) and not _constraint_exists(bind, table_name, constraint_name):
        op.create_unique_constraint(constraint_name, table_name, ["user_id"])


def _drop_unique_user_constraint(table_name: str, constraint_name: str) -> None:
    bind = op.get_bind()
    if _table_exists(bind, table_name) and _constraint_exists(bind, table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name, type_="unique")


def upgrade():
    bind = op.get_bind()
    for table_name in ("sys_user_departments", "sys_user_roles", "sys_user_data_scope_departments"):
        if _table_exists(bind, table_name):
            _delete_duplicate_user_rows(bind, table_name)
    _create_unique_user_constraint("sys_user_departments", "uq_user_departments_user")
    _create_unique_user_constraint("sys_user_roles", "uq_user_roles_user")
    _create_unique_user_constraint("sys_user_data_scope_departments", "uq_user_data_scope_departments_user")


def downgrade():
    _drop_unique_user_constraint("sys_user_data_scope_departments", "uq_user_data_scope_departments_user")
    _drop_unique_user_constraint("sys_user_roles", "uq_user_roles_user")
    _drop_unique_user_constraint("sys_user_departments", "uq_user_departments_user")
