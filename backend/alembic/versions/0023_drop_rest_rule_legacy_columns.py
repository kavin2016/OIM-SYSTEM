"""Drop rest rule legacy columns

Revision ID: 0023_drop_rest_rule_legacy_cols
Revises: 0022_rest_rule_departments
Create Date: 2026-06-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0023_drop_rest_rule_legacy_cols"
down_revision = "0022_rest_rule_departments"
branch_labels = None
depends_on = None


def _drop_foreign_keys_for_columns(table_name, column_names):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    target_columns = set(column_names)
    for fk in inspector.get_foreign_keys(table_name):
        constrained = set(fk.get("constrained_columns") or [])
        if constrained & target_columns and fk.get("name"):
            op.drop_constraint(fk["name"], table_name, type_="foreignkey")


def _drop_indexes_for_columns(table_name, column_names):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    target_columns = set(column_names)
    for index in inspector.get_indexes(table_name):
        indexed = set(index.get("column_names") or [])
        if indexed and indexed <= target_columns and index.get("name"):
            op.drop_index(index["name"], table_name=table_name)


def upgrade():
    table_name = "attendance_rest_rules"
    legacy_columns = ["department_id", "user_id"]
    _drop_foreign_keys_for_columns(table_name, legacy_columns)
    _drop_indexes_for_columns(table_name, legacy_columns)
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column("department_id")
        batch_op.drop_column("user_id")


def downgrade():
    with op.batch_alter_table("attendance_rest_rules") as batch_op:
        batch_op.add_column(sa.Column("department_id", sa.Integer(), nullable=True, comment="部门ID"))
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True, comment="用户ID"))
        batch_op.create_foreign_key(
            "fk_attendance_rest_rules_department_id",
            "departments",
            ["department_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_attendance_rest_rules_user_id",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

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
