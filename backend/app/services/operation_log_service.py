import csv
import io
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.department import Department
from ..models.operation_log import OperationLog
from ..models.user import User
from ..models.user_department import UserDepartment
from .base_service import NotFoundError


SENSITIVE_KEYS = {
    "access_token",
    "captcha",
    "captcha_token",
    "new_password",
    "old_password",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "ssh_private_key_content",
    "token",
}

MODULE_LABELS = {
    "system": "系统管理",
    "ops": "运维管理",
    "attendance": "考勤管理",
}
RESOURCE_TYPE_LABELS = {
    "auth": "认证",
    "department": "部门",
    "domain": "域名",
    "openvpn_account": "OpenVPN账号",
    "openvpn_certificate": "OpenVPN证书",
    "openvpn_log": "OpenVPN连接日志",
    "openvpn_rule": "OpenVPN分配策略",
    "openvpn_server": "OpenVPN服务器",
    "openvpn_session": "OpenVPN会话",
    "openvpn_traffic_alert": "OpenVPN流量告警",
    "openvpn_traffic_threshold": "OpenVPN流量阈值",
    "operation_log": "操作日志",
    "permission": "权限",
    "position": "岗位",
    "role": "角色",
    "user": "用户",
}
ACTION_LABELS = {
    "assign-role": "分配角色",
    "assign-server": "分配服务器",
    "create": "新增",
    "delete": "删除",
    "disable": "禁用",
    "download-config": "下载配置",
    "enable": "启用",
    "export": "导出",
    "issue": "签发",
    "kick": "强制下线",
    "login": "登录",
    "process": "处理",
    "renew": "续期",
    "reset-password": "重置密码",
    "revoke": "吊销",
    "set-default": "设为默认",
    "test": "测试",
    "update": "修改",
}


def sanitize_payload(value: Any, max_list_items: int = 20) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                sanitized[key] = "***"
            else:
                sanitized[key] = sanitize_payload(item, max_list_items=max_list_items)
        return sanitized
    if isinstance(value, list):
        items = [sanitize_payload(item, max_list_items=max_list_items) for item in value[:max_list_items]]
        if len(value) > max_list_items:
            items.append({"truncated": len(value) - max_list_items})
        return items
    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, str) and len(value) > 1000:
            return f"{value[:1000]}..."
        return value
    return str(value)


class OperationLogService:
    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        cursor_id: Optional[int] = None,
        operator_id: Optional[int] = None,
        operator_username: Optional[str] = None,
        department_id: Optional[int] = None,
        department_name: Optional[str] = None,
        module: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        client_ip: Optional[str] = None,
        created_at_start: Optional[datetime] = None,
        created_at_end: Optional[datetime] = None,
        keyword: Optional[str] = None,
    ) -> list[OperationLog]:
        query = self.db.query(OperationLog)
        limit = min(max(limit, 1), 500)
        if cursor_id:
            query = query.filter(OperationLog.id < cursor_id)
        if operator_id:
            query = query.filter(OperationLog.operator_id == operator_id)
        if operator_username:
            query = query.filter(OperationLog.operator_username.like(f"%{operator_username}%"))
        if department_id:
            query = query.filter(OperationLog.department_id == department_id)
        if department_name:
            query = query.filter(OperationLog.department_name.like(f"%{department_name}%"))
        if module:
            query = query.filter(OperationLog.module == module)
        if resource_type:
            query = query.filter(OperationLog.resource_type == resource_type)
        if resource_id:
            query = query.filter(OperationLog.resource_id == resource_id)
        if action:
            query = query.filter(OperationLog.action == action)
        if result:
            query = query.filter(OperationLog.result == result)
        if client_ip:
            query = query.filter(OperationLog.client_ip.like(f"%{client_ip}%"))
        if created_at_start:
            query = query.filter(OperationLog.created_at >= created_at_start)
        if created_at_end:
            query = query.filter(OperationLog.created_at <= created_at_end)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(
                    OperationLog.operator_username.like(like),
                    OperationLog.operator_nickname.like(like),
                    OperationLog.department_name.like(like),
                    OperationLog.module_name.like(like),
                    OperationLog.resource_name.like(like),
                    OperationLog.action_name.like(like),
                    OperationLog.path.like(like),
                    OperationLog.client_ip.like(like),
                    OperationLog.error_message.like(like),
                )
            )
        return query.order_by(OperationLog.id.desc()).offset(skip).limit(limit).all()

    def options(self) -> dict:
        return {
            "modules": self._option_items(OperationLog.module, MODULE_LABELS),
            "resource_types": self._option_items(OperationLog.resource_type, RESOURCE_TYPE_LABELS),
            "actions": self._option_items(OperationLog.action, ACTION_LABELS),
            "results": [
                {"value": "success", "label": "成功"},
                {"value": "failed", "label": "失败"},
            ],
        }

    def get_required(self, log_id: int) -> OperationLog:
        item = self.db.query(OperationLog).filter(OperationLog.id == log_id).first()
        if item is None:
            raise NotFoundError("操作日志不存在")
        return item

    def record(
        self,
        *,
        actor: Optional[User],
        module: str,
        module_name: str,
        resource_type: Optional[str],
        action: str,
        action_name: str,
        resource_id: Optional[int] = None,
        resource_name: Optional[str] = None,
        request: Optional[Request] = None,
        request_body: Any = None,
        response_params: Any = None,
        response_status: int = 200,
        result: str = "success",
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[OperationLog]:
        department_id, department_name = self._operator_department(actor)
        item = OperationLog(
            trace_id=trace_id or uuid.uuid4().hex,
            operator_id=getattr(actor, "id", None),
            operator_username=getattr(actor, "username", None),
            operator_nickname=getattr(actor, "nickname", None),
            department_id=department_id,
            department_name=department_name,
            module=module,
            module_name=module_name,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            action=action,
            action_name=action_name,
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
            duration_ms=duration_ms,
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
        writer.writerow(["ID", "操作时间", "操作人", "部门", "模块", "资源", "动作", "结果", "IP", "状态码", "耗时(ms)"])
        for item in rows:
            writer.writerow(
                [
                    item.id,
                    item.created_at.isoformat(sep=" ", timespec="seconds"),
                    item.operator_username or "",
                    item.department_name or "",
                    item.module_name,
                    item.resource_name or item.resource_type or "",
                    item.action_name,
                    item.result,
                    item.client_ip or "",
                    item.response_status or "",
                    item.duration_ms or "",
                ]
            )
        return "operation-logs.csv", buffer.getvalue()

    def _option_items(self, column, labels: Dict[str, str]) -> List[Dict[str, str]]:
        values = {
            row[0]
            for row in self.db.query(column).filter(column.is_not(None), column != "").distinct().order_by(column.asc()).all()
            if row[0]
        }
        values.update(labels.keys())
        return [{"value": value, "label": labels.get(value, value)} for value in sorted(values, key=lambda item: labels.get(item, item))]

    def _operator_department(self, actor: Optional[User]) -> tuple[Optional[int], Optional[str]]:
        if actor is None or not getattr(actor, "id", None):
            return None, None
        relation = (
            self.db.query(UserDepartment)
            .filter(UserDepartment.user_id == actor.id)
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
