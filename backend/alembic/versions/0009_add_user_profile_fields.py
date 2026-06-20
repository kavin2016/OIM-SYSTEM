"""Add user profile fields

Revision ID: 0009_add_user_profile_fields
Revises: 0008_map_menu_components
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_add_user_profile_fields"
down_revision = "0008_map_menu_components"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("nickname", sa.String(length=64), nullable=True, comment="昵称"))
    op.add_column("users", sa.Column("gender", sa.String(length=16), nullable=True, comment="性别"))
    op.add_column("users", sa.Column("contacts", sa.JSON(), nullable=True, comment="联系方式列表"))


def downgrade():
    op.drop_column("users", "contacts")
    op.drop_column("users", "gender")
    op.drop_column("users", "nickname")
