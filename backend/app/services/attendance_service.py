from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.attendance import (
    AttendanceDailyResult,
    AttendanceMonthlySummary,
    AttendanceRecord,
    AttendanceRequest,
    AttendanceRestRule,
    AttendanceRestRuleDepartment,
    AttendanceRestRuleUser,
    AttendanceScheduleItem,
    AttendanceShift,
)
from ..models.department import Department
from ..models.user import User
from ..models.user_department import UserDepartment
from ..schemas.attendance import (
    AttendanceApproval,
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
    AttendanceRequestCreate,
    AttendanceRequestUpdate,
    AttendanceRestRuleCreate,
    AttendanceRestRuleUpdate,
    AttendanceScheduleCreate,
    AttendanceScheduleUpdate,
    AttendanceShiftCreate,
    AttendanceShiftUpdate,
)
from .base_service import BaseService, ConflictError, NotFoundError


def _combine(day: date, value: time) -> datetime:
    return datetime.combine(day, value)


def _duration_minutes(start_at: datetime, end_at: datetime) -> int:
    return max(0, int((end_at - start_at).total_seconds() // 60))


class AttendanceService(BaseService[AttendanceShift]):
    model = AttendanceShift
    resource_name = "考勤"

    def __init__(self, db: Session):
        super().__init__(db)

    def list_shifts(self, skip: int = 0, limit: int = 100, include_disabled: bool = False, name: Optional[str] = None):
        query = self.db.query(AttendanceShift)
        if not include_disabled:
            query = query.filter(AttendanceShift.is_active.is_(True))
        if name:
            query = query.filter(AttendanceShift.name.like(f"%{name.strip()}%"))
        return query.order_by(AttendanceShift.id.desc()).offset(skip).limit(limit).all()

    def create_shift(self, payload: AttendanceShiftCreate, actor_id: int):
        shift = AttendanceShift(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        return self._commit(shift, "班次名称或编码已存在")

    def update_shift(self, shift_id: int, payload: AttendanceShiftUpdate, actor_id: int):
        shift = self._get_required(AttendanceShift, shift_id, "班次不存在")
        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(shift, field_name, value)
        shift.updated_by = actor_id
        return self._commit(shift, "班次名称或编码已存在")

    def delete_shift(self, shift_id: int, actor_id: int):
        shift = self._get_required(AttendanceShift, shift_id, "班次不存在")
        shift.is_active = False
        shift.updated_by = actor_id
        return self._commit(shift, "班次停用失败")

    def list_rest_rules(self, skip: int = 0, limit: int = 100, include_disabled: bool = False):
        query = self.db.query(AttendanceRestRule)
        if not include_disabled:
            query = query.filter(AttendanceRestRule.is_active.is_(True))
        return query.order_by(AttendanceRestRule.id.desc()).offset(skip).limit(limit).all()

    def create_rest_rule(self, payload: AttendanceRestRuleCreate, actor_id: int):
        department_ids = self._validated_rest_rule_department_ids(payload.department_ids)
        valid_user_ids = self._validated_rest_rule_user_ids(payload.user_ids)
        data = payload.model_dump(exclude={"department_ids", "user_ids"})
        rule = AttendanceRestRule(**data, created_by=actor_id, updated_by=actor_id)
        self._commit(rule, "休息规则创建失败")
        self.replace_rest_rule_departments(rule.id, department_ids, prevalidated=True)
        self.replace_rest_rule_users(rule.id, valid_user_ids, department_ids, prevalidated=True)
        self.db.refresh(rule)
        return rule

    def update_rest_rule(self, rule_id: int, payload: AttendanceRestRuleUpdate, actor_id: int):
        rule = self._get_required(AttendanceRestRule, rule_id, "休息规则不存在")
        update_data = payload.model_dump(exclude_unset=True, exclude={"department_ids", "user_ids"})
        target_department_ids = rule.department_ids
        if "department_ids" in payload.model_fields_set:
            target_department_ids = self._validated_rest_rule_department_ids(payload.department_ids or [])
        valid_user_ids = None
        if "user_ids" in payload.model_fields_set:
            valid_user_ids = self._validated_rest_rule_user_ids(payload.user_ids or [])
        for field_name, value in update_data.items():
            setattr(rule, field_name, value)
        rule.updated_by = actor_id
        self._commit(rule, "休息规则更新失败")
        if "department_ids" in payload.model_fields_set:
            self.replace_rest_rule_departments(rule.id, target_department_ids, prevalidated=True)
        if "user_ids" in payload.model_fields_set:
            self.replace_rest_rule_users(rule.id, valid_user_ids or [], target_department_ids, prevalidated=True)
        self.db.refresh(rule)
        return rule

    def delete_rest_rule(self, rule_id: int, actor_id: int):
        rule = self._get_required(AttendanceRestRule, rule_id, "休息规则不存在")
        rule.is_active = False
        rule.updated_by = actor_id
        return self._commit(rule, "休息规则停用失败")

    def replace_rest_rule_departments(
        self,
        rule_id: int,
        department_ids: Optional[list[int]],
        prevalidated: bool = False,
    ) -> None:
        self.db.query(AttendanceRestRuleDepartment).filter(AttendanceRestRuleDepartment.rest_rule_id == rule_id).delete()
        valid_ids = department_ids if prevalidated else self._validated_rest_rule_department_ids(department_ids or [])
        for department_id in valid_ids:
            self.db.add(AttendanceRestRuleDepartment(rest_rule_id=rule_id, department_id=department_id))
        self.db.commit()

    def replace_rest_rule_users(
        self,
        rule_id: int,
        user_ids: Optional[list[int]],
        department_ids: Optional[list[int]],
        prevalidated: bool = False,
    ) -> None:
        self.db.query(AttendanceRestRuleUser).filter(AttendanceRestRuleUser.rest_rule_id == rule_id).delete()
        valid_ids = user_ids if prevalidated else self._validated_rest_rule_user_ids(user_ids or [])
        for user_id in valid_ids:
            self.db.add(AttendanceRestRuleUser(rest_rule_id=rule_id, user_id=user_id))
        self.db.commit()

    def list_schedules(
        self,
        skip: int = 0,
        limit: int = 200,
        user_id: Optional[int] = None,
        department_id: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ):
        query = self.db.query(AttendanceScheduleItem)
        if user_id:
            query = query.filter(AttendanceScheduleItem.user_id == user_id)
        if department_id:
            query = query.filter(AttendanceScheduleItem.department_id == department_id)
        if start_date:
            query = query.filter(AttendanceScheduleItem.work_date >= start_date)
        if end_date:
            query = query.filter(AttendanceScheduleItem.work_date <= end_date)
        return query.order_by(AttendanceScheduleItem.work_date.desc(), AttendanceScheduleItem.id.desc()).offset(skip).limit(limit).all()

    def create_schedules(self, payload: AttendanceScheduleCreate, actor_id: int):
        self._get_required(AttendanceShift, payload.shift_id, "班次不存在")
        user_ids = self._schedule_user_ids(payload)
        items = []
        current_date = payload.start_date
        while current_date <= payload.end_date:
            for user_id in user_ids:
                department_id = payload.department_id or self._primary_department_id(user_id)
                item = AttendanceScheduleItem(
                    user_id=user_id,
                    department_id=department_id,
                    shift_id=payload.shift_id,
                    work_date=current_date,
                    source_type=payload.source_type,
                    is_temporary=payload.is_temporary or payload.source_type == "temporary",
                    remark=payload.remark,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
                self.db.add(item)
                items.append(item)
            current_date += timedelta(days=1)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError("排班已存在，请调整日期或班次后重试") from exc
        for item in items:
            self.db.refresh(item)
        return items

    def update_schedule(self, schedule_id: int, payload: AttendanceScheduleUpdate, actor_id: int):
        item = self._get_required(AttendanceScheduleItem, schedule_id, "排班不存在")
        update_data = payload.model_dump(exclude_unset=True)
        if "shift_id" in update_data:
            self._get_required(AttendanceShift, update_data["shift_id"], "班次不存在")
        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        item.updated_by = actor_id
        return self._commit(item, "排班更新失败，可能已存在重复排班")

    def delete_schedule(self, schedule_id: int):
        item = self._get_required(AttendanceScheduleItem, schedule_id, "排班不存在")
        self.db.delete(item)
        self.db.commit()
        return item

    def list_records(
        self,
        skip: int = 0,
        limit: int = 200,
        user_id: Optional[int] = None,
        start_at: Optional[datetime] = None,
        end_at: Optional[datetime] = None,
        record_type: Optional[str] = None,
    ):
        query = self.db.query(AttendanceRecord)
        if user_id:
            query = query.filter(AttendanceRecord.user_id == user_id)
        if start_at:
            query = query.filter(AttendanceRecord.record_time >= start_at)
        if end_at:
            query = query.filter(AttendanceRecord.record_time <= end_at)
        if record_type:
            query = query.filter(AttendanceRecord.record_type == record_type)
        return query.order_by(AttendanceRecord.record_time.desc(), AttendanceRecord.id.desc()).offset(skip).limit(limit).all()

    def create_record(self, payload: AttendanceRecordCreate, actor_id: int):
        record = AttendanceRecord(**payload.model_dump(), created_by=actor_id)
        self._apply_record_status(record)
        return self._commit(record, "打卡记录创建失败")

    def update_record(self, record_id: int, payload: AttendanceRecordUpdate):
        record = self._get_required(AttendanceRecord, record_id, "打卡记录不存在")
        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(record, field_name, value)
        self._apply_record_status(record)
        return self._commit(record, "打卡记录更新失败")

    def delete_record(self, record_id: int):
        record = self._get_required(AttendanceRecord, record_id, "打卡记录不存在")
        self.db.delete(record)
        self.db.commit()
        return record

    def list_requests(
        self,
        skip: int = 0,
        limit: int = 200,
        user_id: Optional[int] = None,
        request_type: Optional[str] = None,
        status: Optional[str] = None,
    ):
        query = self.db.query(AttendanceRequest)
        if user_id:
            query = query.filter(AttendanceRequest.user_id == user_id)
        if request_type:
            query = query.filter(AttendanceRequest.request_type == request_type)
        if status:
            query = query.filter(AttendanceRequest.status == status)
        return query.order_by(AttendanceRequest.id.desc()).offset(skip).limit(limit).all()

    def create_request(self, payload: AttendanceRequestCreate):
        request = AttendanceRequest(
            **payload.model_dump(),
            request_no=f"AR{datetime.utcnow():%Y%m%d%H%M%S}{uuid4().hex[:6].upper()}",
            duration_minutes=_duration_minutes(payload.start_at, payload.end_at),
        )
        return self._commit(request, "考勤申请创建失败")

    def update_request(self, request_id: int, payload: AttendanceRequestUpdate):
        request = self._get_required(AttendanceRequest, request_id, "考勤申请不存在")
        if request.status != "pending":
            raise ConflictError("只有待审批申请可以修改")
        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(request, field_name, value)
        request.duration_minutes = _duration_minutes(request.start_at, request.end_at)
        return self._commit(request, "考勤申请更新失败")

    def withdraw_request(self, request_id: int, actor_id: int):
        request = self._get_required(AttendanceRequest, request_id, "考勤申请不存在")
        if request.user_id != actor_id:
            raise ConflictError("只能撤回自己的申请")
        if request.status != "pending":
            raise ConflictError("只有待审批申请可以撤回")
        request.status = "withdrawn"
        return self._commit(request, "撤回申请失败")

    def approve_request(self, request_id: int, payload: AttendanceApproval, actor_id: int):
        request = self._get_required(AttendanceRequest, request_id, "考勤申请不存在")
        if request.status != "pending":
            raise ConflictError("申请已处理")
        if payload.status not in ("approved", "rejected"):
            raise ConflictError("审批状态只能为 approved 或 rejected")
        request.status = payload.status
        request.approver_id = actor_id
        request.approved_at = datetime.utcnow()
        request.approval_remark = payload.approval_remark
        self._commit(request, "审批失败")
        if request.status == "approved":
            self._apply_approved_request(request, actor_id)
        return request

    def rebuild_daily_results(self, work_date: date, user_id: Optional[int] = None):
        schedules = self.list_schedules(user_id=user_id, start_date=work_date, end_date=work_date, limit=10000)
        results = []
        for schedule in schedules:
            result = self._build_daily_result(schedule)
            results.append(result)
        self.db.commit()
        for result in results:
            self.db.refresh(result)
        return results

    def rebuild_monthly_summaries(self, year: int, month: int, user_id: Optional[int] = None):
        start_day = date(year, month, 1)
        end_day = date(year, month, monthrange(year, month)[1])
        query = self.db.query(AttendanceDailyResult).filter(
            AttendanceDailyResult.work_date >= start_day,
            AttendanceDailyResult.work_date <= end_day,
        )
        if user_id:
            query = query.filter(AttendanceDailyResult.user_id == user_id)
        user_ids = [row[0] for row in query.with_entities(AttendanceDailyResult.user_id).distinct().all()]
        summaries = []
        for current_user_id in user_ids:
            rows = query.filter(AttendanceDailyResult.user_id == current_user_id).all()
            summary = self._upsert_monthly_summary(current_user_id, year, month, rows)
            summaries.append(summary)
        self.db.commit()
        for summary in summaries:
            self.db.refresh(summary)
        return summaries

    def list_daily_results(self, skip: int = 0, limit: int = 200, user_id: Optional[int] = None, start_date: Optional[date] = None, end_date: Optional[date] = None):
        query = self.db.query(AttendanceDailyResult)
        if user_id:
            query = query.filter(AttendanceDailyResult.user_id == user_id)
        if start_date:
            query = query.filter(AttendanceDailyResult.work_date >= start_date)
        if end_date:
            query = query.filter(AttendanceDailyResult.work_date <= end_date)
        return query.order_by(AttendanceDailyResult.work_date.desc(), AttendanceDailyResult.id.desc()).offset(skip).limit(limit).all()

    def list_monthly_summaries(self, skip: int = 0, limit: int = 200, user_id: Optional[int] = None, year: Optional[int] = None, month: Optional[int] = None):
        query = self.db.query(AttendanceMonthlySummary)
        if user_id:
            query = query.filter(AttendanceMonthlySummary.user_id == user_id)
        if year:
            query = query.filter(AttendanceMonthlySummary.year == year)
        if month:
            query = query.filter(AttendanceMonthlySummary.month == month)
        return query.order_by(AttendanceMonthlySummary.year.desc(), AttendanceMonthlySummary.month.desc()).offset(skip).limit(limit).all()

    def _apply_record_status(self, record: AttendanceRecord) -> None:
        if not record.shift_id:
            return
        shift = self.db.query(AttendanceShift).filter(AttendanceShift.id == record.shift_id).first()
        if not shift:
            return
        work_date = record.record_time.date()
        if record.schedule_item_id:
            schedule = self.db.query(AttendanceScheduleItem).filter(AttendanceScheduleItem.id == record.schedule_item_id).first()
            if schedule:
                work_date = schedule.work_date
        start_at = _combine(work_date, shift.start_time)
        end_at = _combine(work_date + timedelta(days=1 if shift.is_cross_day else 0), shift.end_time)
        if record.record_type == "checkin":
            allowed = start_at + timedelta(minutes=shift.late_allowed_minutes + (shift.flexible_minutes if shift.is_flexible else 0))
            record.late_minutes = max(0, int((record.record_time - allowed).total_seconds() // 60))
            record.status = "late" if record.late_minutes > 0 else "normal"
        elif record.record_type == "checkout":
            allowed = end_at - timedelta(minutes=shift.early_leave_allowed_minutes)
            record.early_leave_minutes = max(0, int((allowed - record.record_time).total_seconds() // 60))
            record.status = "early_leave" if record.early_leave_minutes > 0 else "normal"

    def _build_daily_result(self, schedule: AttendanceScheduleItem) -> AttendanceDailyResult:
        day_start = _combine(schedule.work_date, time.min)
        day_end = _combine(schedule.work_date + timedelta(days=1), time.max)
        records = self.db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == schedule.user_id,
            AttendanceRecord.record_time >= day_start,
            AttendanceRecord.record_time <= day_end,
            or_(AttendanceRecord.schedule_item_id == schedule.id, AttendanceRecord.shift_id == schedule.shift_id),
        ).all()
        checkins = [record for record in records if record.record_type in ("checkin", "correction")]
        checkouts = [record for record in records if record.record_type == "checkout"]
        checkin = min(checkins, key=lambda item: item.record_time, default=None)
        checkout = max(checkouts, key=lambda item: item.record_time, default=None)
        approved_requests = self.db.query(AttendanceRequest).filter(
            AttendanceRequest.user_id == schedule.user_id,
            AttendanceRequest.status == "approved",
            AttendanceRequest.start_at <= day_end,
            AttendanceRequest.end_at >= day_start,
        ).all()
        leave_minutes = sum(item.duration_minutes for item in approved_requests if item.request_type in ("leave", "compensatory_leave"))
        overtime_minutes = sum(item.duration_minutes for item in approved_requests if item.request_type == "overtime")
        has_rest = self._is_rest_day(schedule) or any(item.request_type == "rest" for item in approved_requests)
        has_business_trip = any(item.request_type == "business_trip" for item in approved_requests)
        has_outing = any(item.request_type == "outing" for item in approved_requests)
        status = "normal"
        is_missing_checkin = checkin is None
        is_missing_checkout = checkout is None
        if has_rest:
            status = "rest"
            is_missing_checkin = False
            is_missing_checkout = False
        elif has_business_trip:
            status = "business_trip"
            is_missing_checkin = False
            is_missing_checkout = False
        elif has_outing:
            status = "outing"
        elif is_missing_checkin or is_missing_checkout:
            status = "missing"
        if is_missing_checkin and is_missing_checkout and leave_minutes == 0:
            status = "absent"
        if leave_minutes > 0:
            status = "leave"
        result = self.db.query(AttendanceDailyResult).filter(
            AttendanceDailyResult.user_id == schedule.user_id,
            AttendanceDailyResult.work_date == schedule.work_date,
            AttendanceDailyResult.shift_id == schedule.shift_id,
        ).first()
        if not result:
            result = AttendanceDailyResult(user_id=schedule.user_id, work_date=schedule.work_date, shift_id=schedule.shift_id)
            self.db.add(result)
        result.schedule_item_id = schedule.id
        result.checkin_time = checkin.record_time if checkin else None
        result.checkout_time = checkout.record_time if checkout else None
        result.status = status
        result.late_minutes = checkin.late_minutes if checkin else 0
        result.early_leave_minutes = checkout.early_leave_minutes if checkout else 0
        result.leave_minutes = leave_minutes
        result.overtime_minutes = overtime_minutes
        result.work_minutes = _duration_minutes(result.checkin_time, result.checkout_time) if result.checkin_time and result.checkout_time else 0
        result.is_missing_checkin = is_missing_checkin
        result.is_missing_checkout = is_missing_checkout
        return result

    def _upsert_monthly_summary(self, user_id: int, year: int, month: int, rows: list[AttendanceDailyResult]) -> AttendanceMonthlySummary:
        summary = self.db.query(AttendanceMonthlySummary).filter(
            AttendanceMonthlySummary.user_id == user_id,
            AttendanceMonthlySummary.year == year,
            AttendanceMonthlySummary.month == month,
        ).first()
        if not summary:
            summary = AttendanceMonthlySummary(user_id=user_id, year=year, month=month)
            self.db.add(summary)
        summary.work_days = len(rows)
        summary.attendance_days = len([row for row in rows if row.status in ("normal", "late", "early_leave", "outing", "business_trip")])
        summary.rest_days = len([row for row in rows if row.status == "rest"])
        summary.late_count = len([row for row in rows if row.late_minutes > 0])
        summary.early_leave_count = len([row for row in rows if row.early_leave_minutes > 0])
        summary.missing_count = len([row for row in rows if row.is_missing_checkin or row.is_missing_checkout])
        summary.absent_days = len([row for row in rows if row.status == "absent"])
        summary.leave_minutes = sum(row.leave_minutes for row in rows)
        summary.overtime_minutes = sum(row.overtime_minutes for row in rows)
        summary.business_trip_days = len([row for row in rows if row.status == "business_trip"])
        return summary

    def _apply_approved_request(self, request: AttendanceRequest, actor_id: int) -> None:
        if request.request_type == "correction":
            record = AttendanceRecord(
                user_id=request.user_id,
                schedule_item_id=request.related_schedule_item_id,
                record_type="correction",
                record_time=request.start_at,
                source="correction",
                status="normal",
                remark=request.reason,
                created_by=actor_id,
            )
            if request.related_schedule_item_id:
                schedule = self.db.query(AttendanceScheduleItem).filter(AttendanceScheduleItem.id == request.related_schedule_item_id).first()
                if schedule:
                    record.shift_id = schedule.shift_id
            self._apply_record_status(record)
            self.db.add(record)
            self.db.commit()
        elif request.request_type == "shift_swap":
            if not request.related_schedule_item_id:
                raise ConflictError("调班申请缺少关联排班")
            schedule = self._get_required(AttendanceScheduleItem, request.related_schedule_item_id, "排班不存在")
            replacement = self._schedule_for_request_time(request.user_id, request.start_at)
            if replacement and replacement.id != schedule.id:
                schedule.shift_id = replacement.shift_id
            schedule.work_date = request.start_at.date()
            schedule.source_type = "swap"
            schedule.is_swapped = True
            schedule.updated_by = actor_id
            self.db.commit()
        self._rebuild_results_for_request(request)

    def _schedule_for_request_time(self, user_id: int, value: datetime) -> Optional[AttendanceScheduleItem]:
        return (
            self.db.query(AttendanceScheduleItem)
            .filter(
                AttendanceScheduleItem.user_id == user_id,
                AttendanceScheduleItem.work_date == value.date(),
            )
            .order_by(AttendanceScheduleItem.id.desc())
            .first()
        )

    def _rebuild_results_for_request(self, request: AttendanceRequest) -> None:
        current = request.start_at.date()
        while current <= request.end_at.date():
            schedules = self.list_schedules(user_id=request.user_id, start_date=current, end_date=current, limit=1000)
            for schedule in schedules:
                self._build_daily_result(schedule)
            current += timedelta(days=1)
        self.db.commit()

    def _is_rest_day(self, schedule: AttendanceScheduleItem) -> bool:
        rules = self.db.query(AttendanceRestRule).filter(AttendanceRestRule.is_active.is_(True)).all()
        weekday = schedule.work_date.weekday()
        for rule in rules:
            if rule.rest_type != "fixed":
                continue
            date_matched = (rule.rest_date is not None and rule.rest_date == schedule.work_date) or (
                rule.weekday is not None and rule.weekday == weekday
            )
            if not date_matched:
                continue
            assigned_department_ids = set(rule.department_ids)
            assigned_user_ids = set(rule.user_ids)
            if not assigned_department_ids and not assigned_user_ids:
                return True
            department_matched = schedule.department_id in assigned_department_ids
            user_matched = schedule.user_id in assigned_user_ids
            if not department_matched and not user_matched:
                continue
            return True
        return False

    def _valid_rest_rule_user_ids(self, user_ids: list[int]) -> list[int]:
        ids = self._normalize_positive_ids(user_ids)
        if not ids:
            return []
        query = self.db.query(User.id).filter(
            User.id.in_(ids),
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
        valid_id_set = {row.id for row in query.all()}
        return [user_id for user_id in ids if user_id in valid_id_set]

    def _validated_rest_rule_user_ids(self, user_ids: list[int]) -> list[int]:
        requested_ids = self._normalize_positive_ids(user_ids or [])
        valid_ids = self._valid_rest_rule_user_ids(requested_ids)
        if requested_ids and len(valid_ids) != len(requested_ids):
            raise ConflictError("员工不存在、已停用或已删除")
        return valid_ids

    def _validated_rest_rule_department_ids(self, department_ids: list[int]) -> list[int]:
        requested_ids = self._normalize_positive_ids(department_ids or [])
        if not requested_ids:
            return []
        rows = (
            self.db.query(Department.id)
            .filter(
                Department.id.in_(requested_ids),
                Department.is_deleted.is_(False),
            )
            .all()
        )
        valid_id_set = {row.id for row in rows}
        valid_ids = [department_id for department_id in requested_ids if department_id in valid_id_set]
        if len(valid_ids) != len(requested_ids):
            raise ConflictError("部门不存在或已删除")
        return valid_ids

    @staticmethod
    def _normalize_positive_ids(values: list[int]) -> list[int]:
        ids = []
        for item in values:
            try:
                item_id = int(item)
            except (TypeError, ValueError):
                continue
            if item_id > 0 and item_id not in ids:
                ids.append(item_id)
        return ids

    def _schedule_user_ids(self, payload: AttendanceScheduleCreate) -> list[int]:
        ids = {int(item) for item in payload.user_ids if int(item) > 0}
        if payload.department_id:
            department = self.db.query(Department).filter(Department.id == payload.department_id, Department.is_deleted.is_(False)).first()
            if not department:
                raise NotFoundError("部门不存在")
            rows = self.db.query(UserDepartment.user_id).filter(UserDepartment.department_id == payload.department_id).all()
            ids.update(row.user_id for row in rows)
        if not ids:
            raise ConflictError("请选择排班人员或部门")
        valid_ids = [
            row.id
            for row in self.db.query(User.id).filter(
                User.id.in_(ids),
                User.is_active.is_(True),
                User.is_deleted.is_(False),
            )
        ]
        if not valid_ids:
            raise ConflictError("没有有效排班人员")
        return valid_ids

    def _primary_department_id(self, user_id: int) -> Optional[int]:
        relation = self.db.query(UserDepartment).filter(UserDepartment.user_id == user_id).order_by(UserDepartment.is_primary.desc()).first()
        return relation.department_id if relation else None

    def _is_now_in_shift_window(self, now: datetime, schedule: AttendanceScheduleItem) -> bool:
        shift = schedule.shift
        start_at = _combine(schedule.work_date, shift.start_time) - timedelta(hours=4)
        end_at = _combine(schedule.work_date + timedelta(days=1 if shift.is_cross_day else 0), shift.end_time) + timedelta(hours=4)
        return start_at <= now <= end_at

    def _ensure_user(self, user_id: int) -> None:
        user = self.db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
        if not user:
            raise NotFoundError("用户不存在")

    def _get_required(self, model, item_id: int, message: str):
        item = self.db.query(model).filter(model.id == item_id).first()
        if item is None:
            raise NotFoundError(message)
        return item

    def _commit(self, item, conflict_message: str):
        self.db.add(item)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(conflict_message) from exc
        self.db.refresh(item)
        return item
