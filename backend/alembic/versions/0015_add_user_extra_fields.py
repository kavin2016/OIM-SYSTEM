"""add user extra fields

Revision ID: 0015_add_user_extra_fields
Revises: 0014_add_role_sort_order
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_add_user_extra_fields"
down_revision = "0014_add_role_sort_order"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("users", "phone"):
        op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True, comment="手机号"))
    if not _has_column("users", "position"):
        op.add_column("users", sa.Column("position", sa.String(length=64), nullable=True, comment="岗位"))
    if not _has_column("users", "remark"):
        op.add_column("users", sa.Column("remark", sa.Text(), nullable=True, comment="备注"))


def downgrade() -> None:
    if _has_column("users", "remark"):
        op.drop_column("users", "remark")
    if _has_column("users", "position"):
        op.drop_column("users", "position")
    if _has_column("users", "phone"):
        op.drop_column("users", "phone")
