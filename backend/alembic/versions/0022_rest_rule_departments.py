"""Add rest rule departments

Revision ID: 0022_rest_rule_departments
Revises: 0021_rest_rule_users
Create Date: 2026-06-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_rest_rule_departments"
down_revision = "0021_rest_rule_users"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attendance_rest_rule_departments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="休息规则部门关系ID"),
        sa.Column("rest_rule_id", sa.Integer(), nullable=False, comment="休息规则ID"),
        sa.Column("department_id", sa.Integer(), nullable=False, comment="部门ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(["rest_rule_id"], ["attendance_rest_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("rest_rule_id", "department_id", name="uq_attendance_rest_rule_department"),
    )
    op.create_index("ix_attendance_rest_rule_departments_id", "attendance_rest_rule_departments", ["id"])
    op.create_index("ix_attendance_rest_rule_departments_rest_rule_id", "attendance_rest_rule_departments", ["rest_rule_id"])
    op.create_index("ix_attendance_rest_rule_departments_department_id", "attendance_rest_rule_departments", ["department_id"])

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO attendance_rest_rule_departments (rest_rule_id, department_id, created_at)
            SELECT id, department_id, CURRENT_TIMESTAMP
            FROM attendance_rest_rules
            WHERE department_id IS NOT NULL
            """
        )
    )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE attendance_rest_rules r
            SET department_id = (
                SELECT MIN(d.department_id)
                FROM attendance_rest_rule_departments d
                WHERE d.rest_rule_id = r.id
            )
            WHERE EXISTS (
                SELECT 1
                FROM attendance_rest_rule_departments d
                WHERE d.rest_rule_id = r.id
            )
            """
        )
    )
    op.drop_index("ix_attendance_rest_rule_departments_department_id", table_name="attendance_rest_rule_departments")
    op.drop_index("ix_attendance_rest_rule_departments_rest_rule_id", table_name="attendance_rest_rule_departments")
    op.drop_index("ix_attendance_rest_rule_departments_id", table_name="attendance_rest_rule_departments")
    op.drop_table("attendance_rest_rule_departments")
