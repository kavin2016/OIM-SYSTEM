"""Add user data scope departments

Revision ID: 0039_user_data_scope
Revises: 0038_update_vpn_menu_paths
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0039_user_data_scope"
down_revision = "0038_update_vpn_menu_paths"
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


def upgrade():
    bind = op.get_bind()
    if _table_exists(bind, "sys_user_data_scope_departments"):
        return
    op.create_table(
        "sys_user_data_scope_departments",
        sa.Column("id", sa.Integer(), nullable=False, comment="用户数据范围部门关系ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("department_id", sa.Integer(), nullable=False, comment="部门ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), comment="创建时间"),
        sa.ForeignKeyConstraint(["department_id"], ["sys_departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["sys_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "department_id", name="uq_user_data_scope_departments_user_department"),
    )
    op.create_index(op.f("ix_sys_user_data_scope_departments_id"), "sys_user_data_scope_departments", ["id"], unique=False)
    op.create_index(op.f("ix_sys_user_data_scope_departments_user_id"), "sys_user_data_scope_departments", ["user_id"], unique=False)
    op.create_index(op.f("ix_sys_user_data_scope_departments_department_id"), "sys_user_data_scope_departments", ["department_id"], unique=False)


def downgrade():
    bind = op.get_bind()
    if _table_exists(bind, "sys_user_data_scope_departments"):
        op.drop_table("sys_user_data_scope_departments")
