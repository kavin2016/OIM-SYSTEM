"""Make user email nullable

Revision ID: 0017_nullable_user_email
Revises: 0016_user_import_export_perms
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0017_nullable_user_email"
down_revision = "0016_user_import_export_perms"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=128),
        nullable=True,
        existing_comment="邮箱",
    )


def downgrade():
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=128),
        nullable=False,
        existing_comment="邮箱",
    )
