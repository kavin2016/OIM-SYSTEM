import csv
import io
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.department import Department
from ..models.login_log import LoginLog
from ..models.user import User
from ..models.user_department import UserDepartment
from .base_service import NotFoundError
from .operation_log_service import sanitize_payload


LOGIN_TYPE_LABELS = {
    "password": "账号密码",
}


class LoginLogService:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        cursor_id: Optional[int] = None,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        department_id: Optional[int] = None,
        department_name: Optional[str] = None,
        login_type: Optional[str] = None,
        result: Optional[str] = None,
        client_ip: Optional[str] = None,
        created_at_start: Optional[datetime] = None,
        created_at_end: Optional[datetime] = None,
        keyword: Optional[str] = None,
    ) -> list[LoginLog]:
        query = self.db.query(LoginLog)
        limit = min(max(limit, 1), 500)
        if cursor_id:
            query = query.filter(LoginLog.id < cursor_id)
        if user_id:
            query = query.filter(LoginLog.user_id == user_id)
        if username:
            query = query.filter(LoginLog.username.like(f"%{username}%"))
        if department_id:
            query = query.filter(LoginLog.department_id == department_id)
        if department_name:
            query = query.filter(LoginLog.department_name.like(f"%{department_name}%"))
        if login_type:
            query = query.filter(LoginLog.login_type == login_type)
        if result:
            query = query.filter(LoginLog.result == result)
        if client_ip:
            query = query.filter(LoginLog.client_ip.like(f"%{client_ip}%"))
        if created_at_start:
            query = query.filter(LoginLog.created_at >= created_at_start)
        if created_at_end:
            query = query.filter(LoginLog.created_at <= created_at_end)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    LoginLog.username.like(like),
                    LoginLog.nickname.like(like),
                    LoginLog.department_name.like(like),
                    LoginLog.path.like(like),
                    LoginLog.client_ip.like(like),
                    LoginLog.error_message.like(like),
                )
            )
        return query.order_by(LoginLog.id.desc()).offset(skip).limit(limit).all()

    def options(self) -> dict:
        return {
            "results": [
                {"value": "success", "label": "成功"},
                {"value": "failed", "label": "失败"},
            ],
            "login_types": self._option_items(LoginLog.login_type, LOGIN_TYPE_LABELS),
        }

    def get_required(self, log_id: int) -> LoginLog:
        item = self.db.query(LoginLog).filter(LoginLog.id == log_id).first()
        if item is None:
            raise NotFoundError("登录日志不存在")
        return item

    def record(
        self,
        *,
        user: Optional[User],
        username: Optional[str],
        request: Optional[Request] = None,
        request_body: Any = None,
        response_params: Any = None,
        response_status: int = 200,
        result: str = "success",
        error_message: Optional[str] = None,
        login_type: str = "password",
        trace_id: Optional[str] = None,
    ) -> Optional[LoginLog]:
        department_id, department_name = self._user_department(user)
        item = LoginLog(
            trace_id=trace_id or uuid.uuid4().hex,
            user_id=getattr(user, "id", None),
            username=getattr(user, "username", None) or username,
            nickname=getattr(user, "nickname", None),
            department_id=department_id,
            department_name=department_name,
            login_type=login_type,
            method=request.method if request else None,
            path=request.url.path if request else None,
            request_params=sanitize_payload(dict(request.query_params)) if request else None,
            request_body=sanitize_payload(request_body),
            response_params=sanitize_payload(response_params),
            response_status=response_status,
            result=result,
            error_message=error_message[:1000] if error_message else None,
            client_ip=self._client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent")[:512] if request and request.headers.get("user-agent") else None,
        )
        try:
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            return item
        except Exception:
            self.db.rollback()
            return None

    def export_csv(self, **filters) -> tuple[str, str]:
        rows = self.list(skip=0, limit=10000, **filters)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["ID", "登录时间", "账号", "昵称", "部门", "登录方式", "结果", "IP", "状态码", "错误信息"])
        for item in rows:
            writer.writerow(
                [
                    item.id,
                    item.created_at.isoformat(sep=" ", timespec="seconds"),
                    item.username or "",
                    item.nickname or "",
                    item.department_name or "",
                    LOGIN_TYPE_LABELS.get(item.login_type, item.login_type),
                    "成功" if item.result == "success" else "失败",
                    item.client_ip or "",
                    item.response_status or "",
                    item.error_message or "",
                ]
            )
        return "login-logs.csv", buffer.getvalue()

    def _option_items(self, column, labels: Dict[str, str]) -> List[Dict[str, str]]:
        values = {
            row[0]
            for row in self.db.query(column).filter(column.is_not(None), column != "").distinct().order_by(column.asc()).all()
            if row[0]
        }
        values.update(labels.keys())
        return [{"value": value, "label": labels.get(value, value)} for value in sorted(values, key=lambda item: labels.get(item, item))]

    def _user_department(self, user: Optional[User]) -> tuple[Optional[int], Optional[str]]:
        if user is None or not getattr(user, "id", None):
            return None, None
        relation = (
            self.db.query(UserDepartment)
            .filter(UserDepartment.user_id == user.id)
            .order_by(UserDepartment.is_primary.desc(), UserDepartment.id.asc())
            .first()
        )
        if relation is None:
            return None, None
        department = self.db.query(Department).filter(Department.id == relation.department_id).first()
        return relation.department_id, department.name if department else None

    def _client_ip(self, request: Optional[Request]) -> Optional[str]:
        if request is None:
            return None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else None
