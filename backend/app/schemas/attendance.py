from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AttendanceShiftBase(BaseModel):
    name: str
    code: str
    start_time: time
    end_time: time
    late_allowed_minutes: int = Field(default=0, ge=0)
    early_leave_allowed_minutes: int = Field(default=0, ge=0)
    is_cross_day: bool = False
    is_flexible: bool = False
    flexible_minutes: int = Field(default=0, ge=0)
    is_active: bool = True


class AttendanceShiftCreate(AttendanceShiftBase):
    pass


class AttendanceShiftUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    late_allowed_minutes: Optional[int] = Field(default=None, ge=0)
    early_leave_allowed_minutes: Optional[int] = Field(default=None, ge=0)
    is_cross_day: Optional[bool] = None
    is_flexible: Optional[bool] = None
    flexible_minutes: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class AttendanceShiftRead(AttendanceShiftBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceRestRuleCreate(BaseModel):
    name: str
    rest_type: str = "fixed"
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    rest_date: Optional[date] = None
    department_ids: list[int] = Field(default_factory=list)
    user_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class AttendanceRestRuleUpdate(BaseModel):
    name: Optional[str] = None
    rest_type: Optional[str] = None
    weekday: Optional[int] = Field(default=None, ge=0, le=6)
    rest_date: Optional[date] = None
    department_ids: Optional[list[int]] = None
    user_ids: Optional[list[int]] = None
    is_active: Optional[bool] = None


class AttendanceRestRuleRead(AttendanceRestRuleCreate):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceScheduleCreate(BaseModel):
    user_ids: list[int] = Field(default_factory=list)
    department_id: Optional[int] = None
    shift_id: int
    start_date: date
    end_date: date
    source_type: str = "user"
    is_temporary: bool = False
    remark: Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def validate_range(cls, value, info):
        start_date = info.data.get("start_date")
        if start_date and value < start_date:
            raise ValueError("结束日期不能早于开始日期")
        return value


class AttendanceScheduleUpdate(BaseModel):
    user_id: Optional[int] = None
    department_id: Optional[int] = None
    shift_id: Optional[int] = None
    work_date: Optional[date] = None
    source_type: Optional[str] = None
    status: Optional[str] = None
    is_temporary: Optional[bool] = None
    is_swapped: Optional[bool] = None
    remark: Optional[str] = None


class AttendanceScheduleRead(BaseModel):
    id: int
    user_id: int
    department_id: Optional[int] = None
    shift_id: int
    work_date: date
    source_type: str
    status: str
    is_temporary: bool
    is_swapped: bool
    remark: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceRecordCreate(BaseModel):
    user_id: int
    schedule_item_id: Optional[int] = None
    shift_id: Optional[int] = None
    record_type: str
    record_time: datetime
    source: str = "manual"
    status: str = "normal"
    remark: Optional[str] = None


class AttendanceRecordUpdate(BaseModel):
    user_id: Optional[int] = None
    schedule_item_id: Optional[int] = None
    shift_id: Optional[int] = None
    record_type: Optional[str] = None
    record_time: Optional[datetime] = None
    source: Optional[str] = None
    status: Optional[str] = None
    late_minutes: Optional[int] = Field(default=None, ge=0)
    early_leave_minutes: Optional[int] = Field(default=None, ge=0)
    remark: Optional[str] = None


class AttendanceRecordRead(BaseModel):
    id: int
    user_id: int
    schedule_item_id: Optional[int] = None
    shift_id: Optional[int] = None
    record_type: str
    record_time: datetime
    source: str
    status: str
    late_minutes: int
    early_leave_minutes: int
    remark: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceRequestCreate(BaseModel):
    user_id: int
    request_type: str
    start_at: datetime
    end_at: datetime
    related_record_id: Optional[int] = None
    related_schedule_item_id: Optional[int] = None
    reason: Optional[str] = None

    @field_validator("end_at")
    @classmethod
    def validate_time_range(cls, value, info):
        start_at = info.data.get("start_at")
        if start_at and value < start_at:
            raise ValueError("结束时间不能早于开始时间")
        return value


class AttendanceRequestUpdate(BaseModel):
    request_type: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    related_record_id: Optional[int] = None
    related_schedule_item_id: Optional[int] = None
    reason: Optional[str] = None
    status: Optional[str] = None


class AttendanceApproval(BaseModel):
    status: str
    approval_remark: Optional[str] = None


class AttendanceRequestRead(BaseModel):
    id: int
    request_no: str
    user_id: int
    request_type: str
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    related_record_id: Optional[int] = None
    related_schedule_item_id: Optional[int] = None
    reason: Optional[str] = None
    status: str
    approver_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    approval_remark: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceDailyResultRead(BaseModel):
    id: int
    user_id: int
    work_date: date
    shift_id: Optional[int] = None
    schedule_item_id: Optional[int] = None
    checkin_time: Optional[datetime] = None
    checkout_time: Optional[datetime] = None
    status: str
    late_minutes: int
    early_leave_minutes: int
    leave_minutes: int
    overtime_minutes: int
    work_minutes: int
    is_missing_checkin: bool
    is_missing_checkout: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceMonthlySummaryRead(BaseModel):
    id: int
    user_id: int
    year: int
    month: int
    work_days: int
    attendance_days: int
    rest_days: int
    late_count: int
    early_leave_count: int
    missing_count: int
    absent_days: int
    leave_minutes: int
    overtime_minutes: int
    business_trip_days: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
