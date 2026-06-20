"""Add attendance module

Revision ID: 0020_attendance_module
Revises: 0019_position_user_rel
Create Date: 2026-06-12 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0020_attendance_module"
down_revision = "0019_position_user_rel"
branch_labels = None
depends_on = None


ATTENDANCE_PERMISSIONS = [
    {
        "name": "考勤管理",
        "code": "attendance:manage:list",
        "type": "menu",
        "path": "/attendance",
        "component": None,
        "icon": "calendar-check",
        "sort_order": 200,
        "description": "考勤管理一级菜单",
        "children": [
            ("Telegram绑定", "attendance:telegram-binding:list", "/attendance/telegram-bindings", "TelegramBindingList", "telegram绑定管理"),
            ("班次管理", "attendance:shift:list", "/attendance/shifts", "AttendanceShiftList", "班次管理"),
            ("休息规则", "attendance:rest-rule:list", "/attendance/rest-rules", "AttendanceRestRuleList", "休息规则管理"),
            ("排班管理", "attendance:schedule:list", "/attendance/schedules", "AttendanceScheduleCalendar", "排班管理"),
            ("打卡记录", "attendance:record:list", "/attendance/records", "AttendanceRecordList", "打卡记录"),
            ("异常申请", "attendance:request:list", "/attendance/requests", "AttendanceRequestList", "异常申请"),
            ("审批管理", "attendance:approval:list", "/attendance/approvals", "AttendanceApprovalList", "审批管理"),
            ("Telegram日志", "attendance:telegram-log:list", "/attendance/telegram-logs", "TelegramLogList", "Telegram原始日志"),
            ("日考勤报表", "attendance:daily-report:list", "/attendance/daily-results", "AttendanceDailyReport", "日考勤报表"),
            ("月考勤报表", "attendance:monthly-report:list", "/attendance/monthly-summaries", "AttendanceMonthlyReport", "月考勤报表"),
        ],
    }
]

BUTTON_PERMISSIONS = [
    ("attendance:telegram-binding:update", "Telegram绑定维护"),
    ("attendance:shift:create", "班次新增"),
    ("attendance:shift:update", "班次修改"),
    ("attendance:shift:delete", "班次删除"),
    ("attendance:rest-rule:update", "休息规则维护"),
    ("attendance:schedule:create", "排班新增"),
    ("attendance:schedule:update", "排班修改"),
    ("attendance:schedule:delete", "排班删除"),
    ("attendance:record:create", "打卡记录新增"),
    ("attendance:record:update", "打卡记录修改"),
    ("attendance:record:delete", "打卡记录删除"),
    ("attendance:request:create", "申请提交"),
    ("attendance:request:withdraw", "申请撤回"),
    ("attendance:approval:approve", "审批处理"),
    ("attendance:approval:reject", "审批驳回"),
    ("attendance:report:export", "报表导出"),
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).scalar()


def _upsert_permission(bind, item, parent_id=None):
    existing_id = _permission_id(bind, item["code"])
    values = {
        "parent_id": parent_id,
        "name": item["name"],
        "code": item["code"],
        "type": item["type"],
        "path": item.get("path"),
        "component": item.get("component"),
        "icon": item.get("icon"),
        "sort_order": item["sort_order"],
        "description": item.get("description"),
        "is_active": True,
        "is_deleted": False,
    }
    if existing_id:
        bind.execute(
            sa.text(
                """
                UPDATE permissions
                SET parent_id = :parent_id, name = :name, type = :type, path = :path,
                    component = :component, icon = :icon, sort_order = :sort_order,
                    description = :description, is_active = :is_active, is_deleted = :is_deleted
                WHERE id = :id
                """
            ),
            {**values, "id": existing_id},
        )
        return existing_id
    result = bind.execute(
        sa.text(
            """
            INSERT INTO permissions
                (parent_id, name, code, type, path, component, icon, sort_order, description, is_active, is_deleted)
            VALUES
                (:parent_id, :name, :code, :type, :path, :component, :icon, :sort_order, :description, :is_active, :is_deleted)
            """
        ),
        values,
    )
    return result.lastrowid


def _grant_to_admin_role(bind, codes):
    admin_role_id = bind.execute(sa.text("SELECT id FROM roles WHERE code = :code AND is_deleted = 0"), {"code": "admin"}).scalar()
    if not admin_role_id:
        return
    permission_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})]
    for permission_id in permission_ids:
        exists = bind.execute(
            sa.text("SELECT id FROM role_permissions WHERE role_id = :role_id AND permission_id = :permission_id"),
            {"role_id": admin_role_id, "permission_id": permission_id},
        ).scalar()
        if not exists:
            bind.execute(
                sa.text("INSERT INTO role_permissions (role_id, permission_id, created_at) VALUES (:role_id, :permission_id, CURRENT_TIMESTAMP)"),
                {"role_id": admin_role_id, "permission_id": permission_id},
            )


def upgrade():
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
        "attendance_shifts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="班次ID"),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True, comment="班次名称"),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True, comment="班次编码"),
        sa.Column("start_time", sa.Time(), nullable=False, comment="上班时间"),
        sa.Column("end_time", sa.Time(), nullable=False, comment="下班时间"),
        sa.Column("late_allowed_minutes", sa.Integer(), nullable=False, server_default="0", comment="允许迟到分钟"),
        sa.Column("early_leave_allowed_minutes", sa.Integer(), nullable=False, server_default="0", comment="允许早退分钟"),
        sa.Column("is_cross_day", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否跨天"),
        sa.Column("is_flexible", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否弹性班"),
        sa.Column("flexible_minutes", sa.Integer(), nullable=False, server_default="0", comment="弹性分钟"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
    )

    op.create_table(
        "attendance_rest_rules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="休息规则ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="规则名称"),
        sa.Column("rest_type", sa.String(length=32), nullable=False, server_default="fixed", comment="休息类型"),
        sa.Column("weekday", sa.Integer(), nullable=True, comment="星期"),
        sa.Column("rest_date", sa.Date(), nullable=True, comment="固定日期"),
        sa.Column("department_id", sa.Integer(), nullable=True, comment="部门ID"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="用户ID"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "attendance_schedule_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="排班明细ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("department_id", sa.Integer(), nullable=True, comment="部门ID"),
        sa.Column("shift_id", sa.Integer(), nullable=False, comment="班次ID"),
        sa.Column("work_date", sa.Date(), nullable=False, comment="工作日期"),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="user", comment="来源"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled", comment="状态"),
        sa.Column("is_temporary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_swapped", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shift_id"], ["attendance_shifts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "work_date", "shift_id", name="uq_attendance_schedule_user_date_shift"),
    )
    op.create_index("ix_attendance_schedule_items_user_id", "attendance_schedule_items", ["user_id"])
    op.create_index("ix_attendance_schedule_items_department_id", "attendance_schedule_items", ["department_id"])
    op.create_index("ix_attendance_schedule_items_shift_id", "attendance_schedule_items", ["shift_id"])
    op.create_index("ix_attendance_schedule_items_work_date", "attendance_schedule_items", ["work_date"])

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

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.String(length=64), nullable=True),
        sa.Column("schedule_item_id", sa.Integer(), nullable=True),
        sa.Column("shift_id", sa.Integer(), nullable=True),
        sa.Column("record_type", sa.String(length=32), nullable=False),
        sa.Column("record_time", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="telegram"),
        sa.Column("source_log_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="normal"),
        sa.Column("late_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_leave_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["schedule_item_id"], ["attendance_schedule_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shift_id"], ["attendance_shifts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_log_id"], ["telegram_attendance_logs.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "attendance_requests",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("request_no", sa.String(length=64), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("related_record_id", sa.Integer(), nullable=True),
        sa.Column("related_schedule_item_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("approver_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approval_remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_record_id"], ["attendance_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_schedule_item_id"], ["attendance_schedule_items.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "attendance_daily_results",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("shift_id", sa.Integer(), nullable=True),
        sa.Column("schedule_item_id", sa.Integer(), nullable=True),
        sa.Column("checkin_time", sa.DateTime(), nullable=True),
        sa.Column("checkout_time", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="normal"),
        sa.Column("late_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_leave_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leave_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overtime_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("work_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_missing_checkin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_missing_checkout", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shift_id"], ["attendance_shifts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["schedule_item_id"], ["attendance_schedule_items.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "work_date", "shift_id", name="uq_attendance_daily_user_date_shift"),
    )

    op.create_table(
        "attendance_monthly_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("work_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attendance_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rest_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("late_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("early_leave_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("absent_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leave_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overtime_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("business_trip_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "year", "month", name="uq_attendance_monthly_user_month"),
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO attendance_shifts
                (name, code, start_time, end_time, late_allowed_minutes, early_leave_allowed_minutes, is_cross_day, is_flexible, flexible_minutes)
            VALUES
                ('早班', 'morning', '07:00:00', '15:00:00', 5, 5, 0, 0, 0),
                ('晚班', 'night', '15:00:00', '23:00:00', 5, 5, 0, 0, 0),
                ('正常班', 'normal', '09:00:00', '18:00:00', 10, 10, 0, 0, 0),
                ('弹性班', 'flexible', '09:00:00', '18:00:00', 0, 10, 0, 1, 60)
            """
        )
    )

    all_codes = []
    for permission in ATTENDANCE_PERMISSIONS:
        parent_id = _upsert_permission(bind, permission, None)
        all_codes.append(permission["code"])
        for index, child in enumerate(permission["children"], start=1):
            child_item = {
                "name": child[0],
                "code": child[1],
                "type": "menu",
                "path": child[2],
                "component": child[3],
                "icon": None,
                "sort_order": permission["sort_order"] * 10 + index,
                "description": child[4],
            }
            _upsert_permission(bind, child_item, parent_id)
            all_codes.append(child[1])
    for index, (code, name) in enumerate(BUTTON_PERMISSIONS, start=1):
        _upsert_permission(
            bind,
            {
                "name": name,
                "code": code,
                "type": "button",
                "path": None,
                "component": None,
                "icon": None,
                "sort_order": 3000 + index,
                "description": name,
            },
            parent_id,
        )
        all_codes.append(code)
    _grant_to_admin_role(bind, all_codes)


def downgrade():
    bind = op.get_bind()
    codes = ["attendance:manage:list"] + [item[1] for item in ATTENDANCE_PERMISSIONS[0]["children"]] + [item[0] for item in BUTTON_PERMISSIONS]
    ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})]
    if ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids"), {"ids": tuple(ids)})
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})

    op.drop_table("attendance_monthly_summaries")
    op.drop_table("attendance_daily_results")
    op.drop_table("attendance_requests")
    op.drop_table("attendance_records")
    op.drop_table("telegram_attendance_logs")
    op.drop_table("telegram_attendance_sessions")
    op.drop_index("ix_attendance_schedule_items_work_date", table_name="attendance_schedule_items")
    op.drop_index("ix_attendance_schedule_items_shift_id", table_name="attendance_schedule_items")
    op.drop_index("ix_attendance_schedule_items_department_id", table_name="attendance_schedule_items")
    op.drop_index("ix_attendance_schedule_items_user_id", table_name="attendance_schedule_items")
    op.drop_table("attendance_schedule_items")
    op.drop_table("attendance_rest_rules")
    op.drop_table("attendance_shifts")
    op.drop_index("ix_telegram_user_bindings_bind_code", table_name="telegram_user_bindings")
    op.drop_index("ix_telegram_user_bindings_telegram_user_id", table_name="telegram_user_bindings")
    op.drop_index("ix_telegram_user_bindings_user_id", table_name="telegram_user_bindings")
    op.drop_table("telegram_user_bindings")
