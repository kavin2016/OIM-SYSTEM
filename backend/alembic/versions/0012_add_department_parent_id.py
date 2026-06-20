"""Add department parent relation

Revision ID: 0012_add_department_parent_id
Revises: 0011_add_user_action_permissions
Create Date: 2026-06-10 21:40:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_add_department_parent_id"
down_revision = "0011_add_user_action_permissions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "departments",
        sa.Column("parent_id", sa.Integer(), nullable=True, comment="上级部门ID"),
    )
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])
    op.create_foreign_key(
        "fk_departments_parent_id_departments",
        "departments",
        "departments",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_departments_parent_id_departments", "departments", type_="foreignkey")
    op.drop_index("ix_departments_parent_id", table_name="departments")
    op.drop_column("departments", "parent_id")
