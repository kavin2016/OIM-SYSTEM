"""add role sort order

Revision ID: 0014_add_role_sort_order
Revises: 0013_add_performance_indexes
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_add_role_sort_order"
down_revision = "0013_add_performance_indexes"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("roles", "sort_order"):
        op.add_column(
            "roles",
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="角色顺序"),
        )


def downgrade() -> None:
    if _has_column("roles", "sort_order"):
        op.drop_column("roles", "sort_order")
