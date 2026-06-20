"""Remove Telegram attendance integration

Revision ID: 0025_remove_telegram_attendance
Revises: 0024_domain_management
Create Date: 2026-06-19 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0025_remove_telegram_attendance"
down_revision = "0024_domain_management"
branch_labels = None
depends_on = None


TELEGRAM_PERMISSION_CODES = (
    "attendance:telegram-binding:list",
    "attendance:telegram-binding:update",
    "attendance:telegram-log:list",
)


def _table_exists(bind, table_name):
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _column_exists(bind, table_name, column_name):
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                  AND COLUMN_NAME = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def _drop_foreign_keys_for_column(bind, table_name, column_name):
    rows = bind.execute(
        sa.text(
            """
            SELECT CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
              AND REFERENCED_TABLE_NAME IS NOT NULL
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).fetchall()
    for row in rows:
        bind.execute(sa.text(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{row[0]}`"))


def _drop_indexes_for_column(bind, table_name, column_name):
    rows = bind.execute(
        sa.text(
            """
            SELECT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = :table_name
              AND COLUMN_NAME = :column_name
              AND INDEX_NAME <> 'PRIMARY'
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).fetchall()
    for row in rows:
        bind.execute(sa.text(f"ALTER TABLE `{table_name}` DROP INDEX `{row[0]}`"))


def _delete_permissions(bind, codes):
    ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})]
    if ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids"), {"ids": tuple(ids)})
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})


def upgrade():
    bind = op.get_bind()
    _delete_permissions(bind, TELEGRAM_PERMISSION_CODES)

    if _table_exists(bind, "attendance_records"):
        if _column_exists(bind, "attendance_records", "source_log_id"):
            _drop_foreign_keys_for_column(bind, "attendance_records", "source_log_id")
            _drop_indexes_for_column(bind, "attendance_records", "source_log_id")
            op.drop_column("attendance_records", "source_log_id")
        if _column_exists(bind, "attendance_records", "telegram_user_id"):
            _drop_indexes_for_column(bind, "attendance_records", "telegram_user_id")
            op.drop_column("attendance_records", "telegram_user_id")
        op.alter_column("attendance_records", "source", server_default="manual", existing_type=sa.String(length=32), nullable=False)

    bind.execute(sa.text("DROP TABLE IF EXISTS `telegram_attendance_logs`"))
    bind.execute(sa.text("DROP TABLE IF EXISTS `telegram_attendance_sessions`"))
    bind.execute(sa.text("DROP TABLE IF EXISTS `telegram_user_bindings`"))


def downgrade():
    bind = op.get_bind()

    if _table_exists(bind, "attendance_records"):
        if not _column_exists(bind, "attendance_records", "telegram_user_id"):
            op.add_column("attendance_records", sa.Column("telegram_user_id", sa.String(length=64), nullable=True))
            op.create_index("ix_attendance_records_telegram_user_id", "attendance_records", ["telegram_user_id"])
        if not _column_exists(bind, "attendance_records", "source_log_id"):
            op.add_column("attendance_records", sa.Column("source_log_id", sa.Integer(), nullable=True))
        op.alter_column("attendance_records", "source", server_default="telegram", existing_type=sa.String(length=32), nullable=False)

    op.create_table(
        "telegram_user_bindings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="Telegram绑定ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="系统用户ID"),
        sa.Column("telegram_user_id", sa.String(length=64), nullable=False, comment="Telegram用户ID"),
        sa.Column("telegram_username", sa.String(length=128), nullable=True, comment="Telegram用户名"),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True, comment="Telegram聊天ID"),
        sa.Column("bind_code", sa.String(length=32), nullable=True, comment="绑定码"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("bound_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="绑定时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_telegram_user_bindings_user_id", "telegram_user_bindings", ["user_id"])
    op.create_index("ix_telegram_user_bindings_telegram_user_id", "telegram_user_bindings", ["telegram_user_id"])
    op.create_index("ix_telegram_user_bindings_bind_code", "telegram_user_bindings", ["bind_code"])

    op.create_table(
        "telegram_attendance_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("telegram_user_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=False),
        sa.Column("schedule_item_id", sa.Integer(), nullable=True),
        sa.Column("session_start_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("session_end_at", sa.DateTime(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shift_id"], ["attendance_shifts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_item_id"], ["attendance_schedule_items.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("telegram_user_id", "shift_date", "shift_id", name="uq_telegram_session_shift"),
    )

    op.create_table(
        "telegram_attendance_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("telegram_update_id", sa.String(length=64), nullable=True, unique=True),
        sa.Column("telegram_user_id", sa.String(length=64), nullable=True),
        sa.Column("telegram_username", sa.String(length=128), nullable=True),
        sa.Column("chat_id", sa.String(length=64), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("processed_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    if _table_exists(bind, "attendance_records") and _column_exists(bind, "attendance_records", "source_log_id"):
        op.create_foreign_key(
            "fk_attendance_records_source_log_id_telegram_logs",
            "attendance_records",
            "telegram_attendance_logs",
            ["source_log_id"],
            ["id"],
            ondelete="SET NULL",
        )
