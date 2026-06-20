"""Add soft delete fields to main tables

Revision ID: 0005_add_is_deleted
Revises: 0004_add_column_comments
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_add_is_deleted"
down_revision = "0004_add_column_comments"
branch_labels = None
depends_on = None

MAIN_TABLES = ("users", "departments", "roles", "permissions")


def upgrade():
    for table_name in MAIN_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
                comment="是否删除：0=未删除，1=已删除",
            ),
        )


def downgrade():
    for table_name in reversed(MAIN_TABLES):
        op.drop_column(table_name, "is_deleted")

