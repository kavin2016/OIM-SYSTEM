import csv
from datetime import date, datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from ..dependencies import AttendanceServiceDep
from ..models.attendance import (
    AttendanceRecord,
    AttendanceRequest,
    AttendanceScheduleItem,
)
from ..schemas.attendance import (
    AttendanceApproval,
    AttendanceDailyResultRead,
    AttendanceMonthlySummaryRead,
    AttendanceRecordCreate,
    AttendanceRecordRead,
    AttendanceRecordUpdate,
    AttendanceRequestCreate,
    AttendanceRequestRead,
    AttendanceRequestUpdate,
    AttendanceRestRuleCreate,
    AttendanceRestRuleRead,
    AttendanceRestRuleUpdate,
    AttendanceScheduleCreate,
    AttendanceScheduleRead,
    AttendanceScheduleUpdate,
    AttendanceShiftCreate,
    AttendanceShiftRead,
    AttendanceShiftUpdate,
)
from ..security import get_current_active_user, require_permission
from ..services.data_scope import ensure_departments_in_scope, ensure_user_in_scope, scoped_user_ids

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.get("/shifts", response_model=list[AttendanceShiftRead])
def list_shifts(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    name: Optional[str] = None,
    current_user=Depends(require_permission("attendance:shift:list")),
):
    return attendance_service.list_shifts(skip, limit, include_disabled, name)


@router.post("/shifts", response_model=AttendanceShiftRead, status_code=status.HTTP_201_CREATED)
def create_shift(
    payload: AttendanceShiftCreate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:shift:create")),
):
    return attendance_service.create_shift(payload, actor_id=current_user.id)


@router.put("/shifts/{shift_id}", response_model=AttendanceShiftRead)
def update_shift(
    shift_id: int,
    payload: AttendanceShiftUpdate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:shift:update")),
):
    return attendance_service.update_shift(shift_id, payload, actor_id=current_user.id)


@router.delete("/shifts/{shift_id}", response_model=AttendanceShiftRead)
def delete_shift(
    shift_id: int,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:shift:delete")),
):
    return attendance_service.delete_shift(shift_id, actor_id=current_user.id)


@router.get("/rest-rules", response_model=list[AttendanceRestRuleRead])
def list_rest_rules(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    current_user=Depends(require_permission("attendance:rest-rule:list")),
):
    return attendance_service.list_rest_rules(skip, limit, include_disabled)


@router.post("/rest-rules", response_model=AttendanceRestRuleRead, status_code=status.HTTP_201_CREATED)
def create_rest_rule(
    payload: AttendanceRestRuleCreate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:rest-rule:update")),
):
    return attendance_service.create_rest_rule(payload, actor_id=current_user.id)


@router.put("/rest-rules/{rule_id}", response_model=AttendanceRestRuleRead)
def update_rest_rule(
    rule_id: int,
    payload: AttendanceRestRuleUpdate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:rest-rule:update")),
):
    return attendance_service.update_rest_rule(rule_id, payload, actor_id=current_user.id)


@router.delete("/rest-rules/{rule_id}", response_model=AttendanceRestRuleRead)
def delete_rest_rule(
    rule_id: int,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:rest-rule:update")),
):
    return attendance_service.delete_rest_rule(rule_id, actor_id=current_user.id)


@router.get("/schedules", response_model=list[AttendanceScheduleRead])
def list_schedules(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 200,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user=Depends(require_permission("attendance:schedule:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.list_schedules(skip, limit, user_id, department_id, start_date, end_date, scope_user_ids=scope_ids)


@router.post("/schedules", response_model=list[AttendanceScheduleRead], status_code=status.HTTP_201_CREATED)
def create_schedules(
    payload: AttendanceScheduleCreate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:schedule:create")),
):
    if payload.department_id:
        ensure_departments_in_scope(attendance_service.db, current_user, [payload.department_id])
    for target_user_id in payload.user_ids:
        ensure_user_in_scope(attendance_service.db, current_user, target_user_id, detail="无权为该用户排班")
    return attendance_service.create_schedules(payload, actor_id=current_user.id)


@router.put("/schedules/{schedule_id}", response_model=AttendanceScheduleRead)
def update_schedule(
    schedule_id: int,
    payload: AttendanceScheduleUpdate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:schedule:update")),
):
    item = attendance_service.db.query(AttendanceScheduleItem).filter(AttendanceScheduleItem.id == schedule_id).first()
    ensure_user_in_scope(attendance_service.db, current_user, item.user_id if item else None, detail="无权修改该排班")
    if payload.user_id:
        ensure_user_in_scope(attendance_service.db, current_user, payload.user_id, detail="无权将排班调整给该用户")
    if payload.department_id:
        ensure_departments_in_scope(attendance_service.db, current_user, [payload.department_id])
    return attendance_service.update_schedule(schedule_id, payload, actor_id=current_user.id)


@router.delete("/schedules/{schedule_id}", response_model=AttendanceScheduleRead)
def delete_schedule(
    schedule_id: int,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:schedule:delete")),
):
    item = attendance_service.db.query(AttendanceScheduleItem).filter(AttendanceScheduleItem.id == schedule_id).first()
    ensure_user_in_scope(attendance_service.db, current_user, item.user_id if item else None, detail="无权删除该排班")
    return attendance_service.delete_schedule(schedule_id)


@router.get("/records", response_model=list[AttendanceRecordRead])
def list_records(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 200,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    record_type: Optional[str] = None,
    current_user=Depends(require_permission("attendance:record:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.list_records(skip, limit, user_id, start_at, end_at, record_type, scope_user_ids=scope_ids)


@router.post("/records", response_model=AttendanceRecordRead, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: AttendanceRecordCreate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:record:create")),
):
    ensure_user_in_scope(attendance_service.db, current_user, payload.user_id, detail="无权为该用户创建打卡记录")
    return attendance_service.create_record(payload, actor_id=current_user.id)


@router.put("/records/{record_id}", response_model=AttendanceRecordRead)
def update_record(
    record_id: int,
    payload: AttendanceRecordUpdate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:record:update")),
):
    item = attendance_service.db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    ensure_user_in_scope(attendance_service.db, current_user, item.user_id if item else None, detail="无权修改该打卡记录")
    if payload.user_id:
        ensure_user_in_scope(attendance_service.db, current_user, payload.user_id, detail="无权将打卡记录调整给该用户")
    return attendance_service.update_record(record_id, payload)


@router.delete("/records/{record_id}", response_model=AttendanceRecordRead)
def delete_record(
    record_id: int,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:record:delete")),
):
    item = attendance_service.db.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
    ensure_user_in_scope(attendance_service.db, current_user, item.user_id if item else None, detail="无权删除该打卡记录")
    return attendance_service.delete_record(record_id)


@router.get("/requests", response_model=list[AttendanceRequestRead])
def list_requests(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 200,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    request_type: Optional[str] = None,
    request_status: Optional[str] = None,
    current_user=Depends(require_permission("attendance:request:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.list_requests(skip, limit, user_id, request_type, request_status, scope_user_ids=scope_ids)


@router.post("/requests", response_model=AttendanceRequestRead, status_code=status.HTTP_201_CREATED)
def create_request(
    payload: AttendanceRequestCreate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(get_current_active_user),
):
    if not current_user.is_admin and payload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能提交自己的申请")
    return attendance_service.create_request(payload)


@router.put("/requests/{request_id}", response_model=AttendanceRequestRead)
def update_request(
    request_id: int,
    payload: AttendanceRequestUpdate,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:request:create")),
):
    item = attendance_service.db.query(AttendanceRequest).filter(AttendanceRequest.id == request_id).first()
    ensure_user_in_scope(attendance_service.db, current_user, item.user_id if item else None, detail="无权修改该考勤申请")
    return attendance_service.update_request(request_id, payload)


@router.post("/requests/{request_id}/withdraw", response_model=AttendanceRequestRead)
def withdraw_request(
    request_id: int,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(get_current_active_user),
):
    return attendance_service.withdraw_request(request_id, actor_id=current_user.id)


@router.post("/requests/{request_id}/approve", response_model=AttendanceRequestRead)
def approve_request(
    request_id: int,
    payload: AttendanceApproval,
    attendance_service: AttendanceServiceDep,
    current_user=Depends(require_permission("attendance:approval:approve")),
):
    item = attendance_service.db.query(AttendanceRequest).filter(AttendanceRequest.id == request_id).first()
    ensure_user_in_scope(attendance_service.db, current_user, item.user_id if item else None, detail="无权审批该考勤申请")
    return attendance_service.approve_request(request_id, payload, actor_id=current_user.id)


@router.get("/daily-results", response_model=list[AttendanceDailyResultRead])
def list_daily_results(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 200,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user=Depends(require_permission("attendance:daily-report:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.list_daily_results(skip, limit, user_id, start_date, end_date, scope_user_ids=scope_ids)


@router.get("/daily-results/export")
def export_daily_results(
    attendance_service: AttendanceServiceDep,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user=Depends(require_permission("attendance:report:export")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    rows = attendance_service.list_daily_results(0, 10000, user_id, start_date, end_date, scope_user_ids=scope_ids)
    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["日期", "用户ID", "班次ID", "上班打卡", "下班打卡", "状态", "迟到分钟", "早退分钟", "请假分钟", "加班分钟", "出勤分钟"])
    for row in rows:
        writer.writerow([
            row.work_date,
            row.user_id,
            row.shift_id or "",
            row.checkin_time or "",
            row.checkout_time or "",
            row.status,
            row.late_minutes,
            row.early_leave_minutes,
            row.leave_minutes,
            row.overtime_minutes,
            row.work_minutes,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=attendance_daily_report.csv"},
    )


@router.post("/daily-results/rebuild", response_model=list[AttendanceDailyResultRead])
def rebuild_daily_results(
    work_date: date,
    attendance_service: AttendanceServiceDep,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("attendance:daily-report:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.rebuild_daily_results(work_date, user_id, scope_user_ids=scope_ids)


@router.get("/monthly-summaries", response_model=list[AttendanceMonthlySummaryRead])
def list_monthly_summaries(
    attendance_service: AttendanceServiceDep,
    skip: int = 0,
    limit: int = 200,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user=Depends(require_permission("attendance:monthly-report:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.list_monthly_summaries(skip, limit, user_id, year, month, scope_user_ids=scope_ids)


@router.get("/monthly-summaries/export")
def export_monthly_summaries(
    attendance_service: AttendanceServiceDep,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user=Depends(require_permission("attendance:report:export")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    rows = attendance_service.list_monthly_summaries(0, 10000, user_id, year, month, scope_user_ids=scope_ids)
    output = StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["年份", "月份", "用户ID", "应出勤", "实出勤", "休息", "迟到", "早退", "缺卡", "旷工", "请假分钟", "加班分钟", "出差天数"])
    for row in rows:
        writer.writerow([
            row.year,
            row.month,
            row.user_id,
            row.work_days,
            row.attendance_days,
            row.rest_days,
            row.late_count,
            row.early_leave_count,
            row.missing_count,
            row.absent_days,
            row.leave_minutes,
            row.overtime_minutes,
            row.business_trip_days,
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=attendance_monthly_report.csv"},
    )


@router.post("/monthly-summaries/rebuild", response_model=list[AttendanceMonthlySummaryRead])
def rebuild_monthly_summaries(
    year: int,
    month: int,
    attendance_service: AttendanceServiceDep,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("attendance:monthly-report:list")),
):
    scope_ids = scoped_user_ids(attendance_service.db, current_user, user_id=user_id, department_id=department_id)
    return attendance_service.rebuild_monthly_summaries(year, month, user_id, scope_user_ids=scope_ids)
