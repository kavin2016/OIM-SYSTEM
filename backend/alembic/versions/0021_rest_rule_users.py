"""Add rest rule users

Revision ID: 0021_rest_rule_users
Revises: 0020_attendance_module
Create Date: 2026-06-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_rest_rule_users"
down_revision = "0020_attendance_module"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attendance_rest_rule_users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="休息规则员工关系ID"),
        sa.Column("rest_rule_id", sa.Integer(), nullable=False, comment="休息规则ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(["rest_rule_id"], ["attendance_rest_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("rest_rule_id", "user_id", name="uq_attendance_rest_rule_user"),
    )
    op.create_index("ix_attendance_rest_rule_users_id", "attendance_rest_rule_users", ["id"])
    op.create_index("ix_attendance_rest_rule_users_rest_rule_id", "attendance_rest_rule_users", ["rest_rule_id"])
    op.create_index("ix_attendance_rest_rule_users_user_id", "attendance_rest_rule_users", ["user_id"])

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO attendance_rest_rule_users (rest_rule_id, user_id, created_at)
            SELECT id, user_id, CURRENT_TIMESTAMP
            FROM attendance_rest_rules
            WHERE user_id IS NOT NULL
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE attendance_rest_rules r
            SET user_id = (
                SELECT MIN(u.user_id)
                FROM attendance_rest_rule_users u
                WHERE u.rest_rule_id = r.id
            )
            WHERE EXISTS (
                SELECT 1
                FROM attendance_rest_rule_users u
                WHERE u.rest_rule_id = r.id
            )
            """
        )
    )
    op.drop_index("ix_attendance_rest_rule_users_user_id", table_name="attendance_rest_rule_users")
    op.drop_index("ix_attendance_rest_rule_users_rest_rule_id", table_name="attendance_rest_rule_users")
    op.drop_index("ix_attendance_rest_rule_users_id", table_name="attendance_rest_rule_users")
    op.drop_table("attendance_rest_rule_users")
