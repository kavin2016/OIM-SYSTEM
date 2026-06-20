from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class AttendanceShift(Base):
    __tablename__ = "attendance_shifts"

    id = Column(Integer, primary_key=True, index=True, comment="班次ID")
    name = Column(String(64), unique=True, nullable=False, comment="班次名称")
    code = Column(String(64), unique=True, nullable=False, comment="班次编码")
    start_time = Column(Time, nullable=False, comment="上班时间")
    end_time = Column(Time, nullable=False, comment="下班时间")
    late_allowed_minutes = Column(Integer, default=0, nullable=False, comment="允许迟到分钟")
    early_leave_allowed_minutes = Column(Integer, default=0, nullable=False, comment="允许早退分钟")
    is_cross_day = Column(Boolean, default=False, nullable=False, comment="是否跨天")
    is_flexible = Column(Boolean, default=False, nullable=False, comment="是否弹性班")
    flexible_minutes = Column(Integer, default=0, nullable=False, comment="弹性分钟")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="更新人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class AttendanceRestRule(Base):
    __tablename__ = "attendance_rest_rules"

    id = Column(Integer, primary_key=True, index=True, comment="休息规则ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    rest_type = Column(String(32), default="fixed", nullable=False, comment="休息类型：fixed/request")
    weekday = Column(Integer, nullable=True, comment="星期：0-6")
    rest_date = Column(Date, nullable=True, comment="固定休息日期")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="更新人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")

    departments = relationship("AttendanceRestRuleDepartment", back_populates="rule", cascade="all, delete-orphan")
    users = relationship("AttendanceRestRuleUser", back_populates="rule", cascade="all, delete-orphan")

    @property
    def department_ids(self):
        return [item.department_id for item in self.departments]

    @property
    def user_ids(self):
        return [item.user_id for item in self.users]


class AttendanceRestRuleDepartment(Base):
    __tablename__ = "attendance_rest_rule_departments"
    __table_args__ = (UniqueConstraint("rest_rule_id", "department_id", name="uq_attendance_rest_rule_department"),)

    id = Column(Integer, primary_key=True, index=True, comment="休息规则部门关系ID")
    rest_rule_id = Column(Integer, ForeignKey("attendance_rest_rules.id", ondelete="CASCADE"), nullable=False, index=True, comment="休息规则ID")
    department_id = Column(Integer, ForeignKey("sys_departments.id", ondelete="CASCADE"), nullable=False, index=True, comment="部门ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    rule = relationship("AttendanceRestRule", back_populates="departments")
    department = relationship("Department")


class AttendanceRestRuleUser(Base):
    __tablename__ = "attendance_rest_rule_users"
    __table_args__ = (UniqueConstraint("rest_rule_id", "user_id", name="uq_attendance_rest_rule_user"),)

    id = Column(Integer, primary_key=True, index=True, comment="休息规则员工关系ID")
    rest_rule_id = Column(Integer, ForeignKey("attendance_rest_rules.id", ondelete="CASCADE"), nullable=False, index=True, comment="休息规则ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    rule = relationship("AttendanceRestRule", back_populates="users")
    user = relationship("User")


class AttendanceScheduleItem(Base):
    __tablename__ = "attendance_schedule_items"
    __table_args__ = (UniqueConstraint("user_id", "work_date", "shift_id", name="uq_attendance_schedule_user_date_shift"),)

    id = Column(Integer, primary_key=True, index=True, comment="排班明细ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    department_id = Column(Integer, ForeignKey("sys_departments.id", ondelete="SET NULL"), nullable=True, index=True, comment="部门ID")
    shift_id = Column(Integer, ForeignKey("attendance_shifts.id", ondelete="RESTRICT"), nullable=False, index=True, comment="班次ID")
    work_date = Column(Date, nullable=False, index=True, comment="工作日期")
    source_type = Column(String(32), default="user", nullable=False, comment="来源：user/department/batch/temporary/swap")
    status = Column(String(32), default="scheduled", nullable=False, comment="状态")
    is_temporary = Column(Boolean, default=False, nullable=False, comment="是否临时排班")
    is_swapped = Column(Boolean, default=False, nullable=False, comment="是否调班")
    remark = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="更新人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")

    user = relationship("User")
    shift = relationship("AttendanceShift")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True, comment="打卡记录ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    schedule_item_id = Column(Integer, ForeignKey("attendance_schedule_items.id", ondelete="SET NULL"), nullable=True, index=True, comment="排班明细ID")
    shift_id = Column(Integer, ForeignKey("attendance_shifts.id", ondelete="SET NULL"), nullable=True, index=True, comment="班次ID")
    record_type = Column(String(32), nullable=False, comment="记录类型：checkin/checkout/correction")
    record_time = Column(DateTime, nullable=False, index=True, comment="打卡时间")
    source = Column(String(32), default="manual", nullable=False, comment="来源")
    status = Column(String(32), default="normal", nullable=False, comment="状态")
    late_minutes = Column(Integer, default=0, nullable=False, comment="迟到分钟")
    early_leave_minutes = Column(Integer, default=0, nullable=False, comment="早退分钟")
    remark = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")

    user = relationship("User")
    shift = relationship("AttendanceShift")


class AttendanceRequest(Base):
    __tablename__ = "attendance_requests"

    id = Column(Integer, primary_key=True, index=True, comment="考勤申请ID")
    request_no = Column(String(64), unique=True, nullable=False, comment="申请编号")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="申请用户ID")
    request_type = Column(String(32), nullable=False, index=True, comment="申请类型")
    start_at = Column(DateTime, nullable=False, comment="开始时间")
    end_at = Column(DateTime, nullable=False, comment="结束时间")
    duration_minutes = Column(Integer, default=0, nullable=False, comment="时长分钟")
    related_record_id = Column(Integer, ForeignKey("attendance_records.id", ondelete="SET NULL"), nullable=True, comment="关联打卡记录ID")
    related_schedule_item_id = Column(Integer, ForeignKey("attendance_schedule_items.id", ondelete="SET NULL"), nullable=True, comment="关联排班ID")
    reason = Column(Text, nullable=True, comment="申请原因")
    status = Column(String(32), default="pending", nullable=False, index=True, comment="审批状态")
    approver_id = Column(Integer, ForeignKey("sys_users.id", ondelete="SET NULL"), nullable=True, comment="审批人ID")
    approved_at = Column(DateTime, nullable=True, comment="审批时间")
    approval_remark = Column(Text, nullable=True, comment="审批备注")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")

    user = relationship("User", foreign_keys=[user_id])


class AttendanceDailyResult(Base):
    __tablename__ = "attendance_daily_results"
    __table_args__ = (UniqueConstraint("user_id", "work_date", "shift_id", name="uq_attendance_daily_user_date_shift"),)

    id = Column(Integer, primary_key=True, index=True, comment="日考勤结果ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    work_date = Column(Date, nullable=False, index=True, comment="考勤日期")
    shift_id = Column(Integer, ForeignKey("attendance_shifts.id", ondelete="SET NULL"), nullable=True, index=True, comment="班次ID")
    schedule_item_id = Column(Integer, ForeignKey("attendance_schedule_items.id", ondelete="SET NULL"), nullable=True, comment="排班明细ID")
    checkin_time = Column(DateTime, nullable=True, comment="上班打卡时间")
    checkout_time = Column(DateTime, nullable=True, comment="下班打卡时间")
    status = Column(String(32), default="normal", nullable=False, comment="状态")
    late_minutes = Column(Integer, default=0, nullable=False, comment="迟到分钟")
    early_leave_minutes = Column(Integer, default=0, nullable=False, comment="早退分钟")
    leave_minutes = Column(Integer, default=0, nullable=False, comment="请假分钟")
    overtime_minutes = Column(Integer, default=0, nullable=False, comment="加班分钟")
    work_minutes = Column(Integer, default=0, nullable=False, comment="出勤分钟")
    is_missing_checkin = Column(Boolean, default=False, nullable=False, comment="是否缺上班卡")
    is_missing_checkout = Column(Boolean, default=False, nullable=False, comment="是否缺下班卡")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class AttendanceMonthlySummary(Base):
    __tablename__ = "attendance_monthly_summaries"
    __table_args__ = (UniqueConstraint("user_id", "year", "month", name="uq_attendance_monthly_user_month"),)

    id = Column(Integer, primary_key=True, index=True, comment="月考勤汇总ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    year = Column(Integer, nullable=False, index=True, comment="年份")
    month = Column(Integer, nullable=False, index=True, comment="月份")
    work_days = Column(Integer, default=0, nullable=False, comment="应出勤天数")
    attendance_days = Column(Integer, default=0, nullable=False, comment="实际出勤天数")
    rest_days = Column(Integer, default=0, nullable=False, comment="休息天数")
    late_count = Column(Integer, default=0, nullable=False, comment="迟到次数")
    early_leave_count = Column(Integer, default=0, nullable=False, comment="早退次数")
    missing_count = Column(Integer, default=0, nullable=False, comment="缺卡次数")
    absent_days = Column(Integer, default=0, nullable=False, comment="旷工天数")
    leave_minutes = Column(Integer, default=0, nullable=False, comment="请假分钟")
    overtime_minutes = Column(Integer, default=0, nullable=False, comment="加班分钟")
    business_trip_days = Column(Integer, default=0, nullable=False, comment="出差天数")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
