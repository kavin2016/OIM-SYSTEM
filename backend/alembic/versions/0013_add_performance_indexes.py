"""Add performance indexes

Revision ID: 0013_add_performance_indexes
Revises: 0012_add_department_parent_id
Create Date: 2026-06-11 14:05:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_add_performance_indexes"
down_revision = "0012_add_department_parent_id"
branch_labels = None
depends_on = None


def index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if not index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def drop_index_if_exists(index_name: str, table_name: str) -> None:
    if index_exists(table_name, index_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade():
    create_index_if_missing("ix_users_deleted_active_id", "users", ["is_deleted", "is_active", "id"])
    create_index_if_missing("ix_departments_deleted_active_id", "departments", ["is_deleted", "is_active", "id"])
    create_index_if_missing("ix_roles_deleted_active_id", "roles", ["is_deleted", "is_active", "id"])
    create_index_if_missing(
        "ix_permissions_deleted_active_type_sort",
        "permissions",
        ["is_deleted", "is_active", "type", "sort_order", "id"],
    )
    create_index_if_missing("ix_user_departments_department_id", "user_departments", ["department_id"])
    create_index_if_missing("ix_user_roles_role_id", "user_roles", ["role_id"])
    create_index_if_missing("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])


def downgrade():
    drop_index_if_exists("ix_role_permissions_permission_id", "role_permissions")
    drop_index_if_exists("ix_user_roles_role_id", "user_roles")
    drop_index_if_exists("ix_user_departments_department_id", "user_departments")
    drop_index_if_exists("ix_permissions_deleted_active_type_sort", "permissions")
    drop_index_if_exists("ix_roles_deleted_active_id", "roles")
    drop_index_if_exists("ix_departments_deleted_active_id", "departments")
    drop_index_if_exists("ix_users_deleted_active_id", "users")
