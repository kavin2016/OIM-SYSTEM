"""Add audit fields to main tables

Revision ID: 0003_add_audit_fields
Revises: 0002_add_org_rbac_tables
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_add_audit_fields"
down_revision = "0002_add_org_rbac_tables"
branch_labels = None
depends_on = None

MAIN_TABLES = ("users", "departments", "roles", "permissions")


def upgrade():
    for table_name in MAIN_TABLES:
        op.add_column(table_name, sa.Column("created_by", sa.Integer(), nullable=True))
        op.add_column(table_name, sa.Column("updated_by", sa.Integer(), nullable=True))

    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade():
    op.drop_column("users", "updated_at")

    for table_name in reversed(MAIN_TABLES):
        op.drop_column(table_name, "updated_by")
        op.drop_column(table_name, "created_by")

