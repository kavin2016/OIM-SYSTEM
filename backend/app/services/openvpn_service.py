from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models.department import Department
from ..models.openvpn import (
    OpenVpnAccount,
    OpenVpnAssignmentRule,
    OpenVpnCertificate,
    OpenVpnConnectionLog,
    OpenVpnServer,
    OpenVpnSession,
)
from ..models.position import Position
from ..models.role import Role
from ..models.user import User
from ..models.user_department import UserDepartment
from ..models.user_position import UserPosition
from ..models.user_role import UserRole
from ..schemas.openvpn import (
    OpenVpnAssignmentRuleCreate,
    OpenVpnAssignmentRuleUpdate,
    OpenVpnServerCreate,
    OpenVpnServerUpdate,
)
from .base_service import BaseService, ConflictError, NotFoundError


class OpenVpnService(BaseService[OpenVpnServer]):
    model = OpenVpnServer
    resource_name = "OpenVPN服务器"

    def __init__(self, db: Session):
        super().__init__(db)

    def list_servers(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
        name: Optional[str] = None,
        code: Optional[str] = None,
        status: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[OpenVpnServer]:
        query = self.db.query(OpenVpnServer)
        if not include_deleted:
            query = query.filter(OpenVpnServer.is_deleted.is_(False))
        if not include_disabled:
            query = query.filter(OpenVpnServer.is_active.is_(True))
        if name:
            query = query.filter(OpenVpnServer.name.like(f"%{name.strip()}%"))
        if code:
            query = query.filter(OpenVpnServer.code.like(f"%{code.strip()}%"))
        if status:
            query = query.filter(OpenVpnServer.status == status)
        if region:
            query = query.filter(OpenVpnServer.region.like(f"%{region.strip()}%"))
        return query.order_by(OpenVpnServer.is_default.desc(), OpenVpnServer.id.desc()).offset(skip).limit(limit).all()

    def create_server(self, payload: OpenVpnServerCreate, actor_id: int) -> OpenVpnServer:
        server = OpenVpnServer(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        if server.is_default:
            self._clear_default_server()
        return self.commit(server, "OpenVPN服务器名称或编码已存在")

    def update_server(self, server_id: int, payload: OpenVpnServerUpdate, actor_id: int) -> OpenVpnServer:
        server = self.get_server_required(server_id, include_deleted=True)
        update_data = payload.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(server, field_name, value)
        if server.is_default:
            self._clear_default_server(except_id=server.id)
        if server.is_deleted:
            server.is_active = False
            server.status = "disabled"
        server.updated_by = actor_id
        return self.commit(server, "OpenVPN服务器名称或编码已存在")

    def delete_server(self, server_id: int, actor_id: int) -> OpenVpnServer:
        server = self.get_server_required(server_id)
        server.is_deleted = True
        server.is_active = False
        server.is_default = False
        server.status = "disabled"
        server.updated_by = actor_id
        return self.commit(server, "OpenVPN服务器删除失败")

    def set_default_server(self, server_id: int, actor_id: int) -> OpenVpnServer:
        server = self.get_server_required(server_id)
        self._clear_default_server(except_id=server.id)
        server.is_default = True
        server.is_active = True
        server.updated_by = actor_id
        return self.commit(server, "设置默认服务器失败")

    def test_server(self, server_id: int) -> dict:
        server = self.get_server_required(server_id)
        return {
            "ok": server.is_active and server.status != "disabled",
            "message": "服务器配置可用，真实连通性测试请接入 OpenVPN management interface",
        }

    def get_server_required(self, server_id: int, include_deleted: bool = False) -> OpenVpnServer:
        query = self.db.query(OpenVpnServer).filter(OpenVpnServer.id == server_id)
        if not include_deleted:
            query = query.filter(OpenVpnServer.is_deleted.is_(False))
        server = query.first()
        if not server:
            raise NotFoundError("OpenVPN服务器不存在")
        return server

    def list_rules(
        self,
        skip: int = 0,
        limit: int = 100,
        server_id: Optional[int] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> list[OpenVpnAssignmentRule]:
        query = self.db.query(OpenVpnAssignmentRule)
        if server_id:
            query = query.filter(OpenVpnAssignmentRule.server_id == server_id)
        if target_type:
            query = query.filter(OpenVpnAssignmentRule.target_type == target_type)
        if target_id:
            query = query.filter(OpenVpnAssignmentRule.target_id == target_id)
        if is_active is not None:
            query = query.filter(OpenVpnAssignmentRule.is_active.is_(is_active))
        return query.order_by(OpenVpnAssignmentRule.priority.asc(), OpenVpnAssignmentRule.id.desc()).offset(skip).limit(limit).all()

    def create_rule(self, payload: OpenVpnAssignmentRuleCreate, actor_id: int) -> OpenVpnAssignmentRule:
        self.get_server_required(payload.server_id)
        self._ensure_rule_target_exists(payload.target_type, payload.target_id)
        rule = OpenVpnAssignmentRule(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        return self.commit(rule, "OpenVPN分配规则已存在")

    def update_rule(self, rule_id: int, payload: OpenVpnAssignmentRuleUpdate, actor_id: int) -> OpenVpnAssignmentRule:
        rule = self.get_rule_required(rule_id)
        update_data = payload.model_dump(exclude_unset=True)
        target_type = update_data.get("target_type", rule.target_type)
        target_id = update_data.get("target_id", rule.target_id)
        if "server_id" in update_data:
            self.get_server_required(update_data["server_id"])
        if "target_type" in update_data or "target_id" in update_data:
            self._ensure_rule_target_exists(target_type, target_id)
        for field_name, value in update_data.items():
            setattr(rule, field_name, value)
        rule.updated_by = actor_id
        return self.commit(rule, "OpenVPN分配规则已存在")

    def delete_rule(self, rule_id: int) -> OpenVpnAssignmentRule:
        rule = self.get_rule_required(rule_id)
        self.db.delete(rule)
        self.db.commit()
        return rule

    def get_rule_required(self, rule_id: int) -> OpenVpnAssignmentRule:
        rule = self.db.query(OpenVpnAssignmentRule).filter(OpenVpnAssignmentRule.id == rule_id).first()
        if not rule:
            raise NotFoundError("OpenVPN分配规则不存在")
        return rule

    def list_accounts(
        self,
        skip: int = 0,
        limit: int = 100,
        username: Optional[str] = None,
        status: Optional[str] = None,
        server_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> list[OpenVpnAccount]:
        query = self.db.query(OpenVpnAccount).join(User, User.id == OpenVpnAccount.user_id)
        if username:
            keyword = f"%{username.strip()}%"
            query = query.filter(or_(User.username.like(keyword), User.nickname.like(keyword)))
        if status:
            query = query.filter(OpenVpnAccount.status == status)
        if server_id:
            query = query.filter(OpenVpnAccount.server_id == server_id)
        if department_id:
            query = query.join(UserDepartment, UserDepartment.user_id == User.id).filter(UserDepartment.department_id == department_id)
        return query.order_by(OpenVpnAccount.id.desc()).offset(skip).limit(limit).all()

    def enable_account(self, user_id: int, payload, actor_id: int) -> OpenVpnAccount:
        user = self._get_active_user_required(user_id)
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.user_id == user.id).first()
        if not account:
            resolved_server, assign_source, rule_id = self.resolve_user_server(user.id, preferred_server_id=payload.server_id)
            account = OpenVpnAccount(
                user_id=user.id,
                server_id=resolved_server.id if resolved_server else None,
                vpn_username=payload.vpn_username or user.username,
                status="enabled",
                assign_source=assign_source,
                assignment_rule_id=rule_id,
                remark=payload.remark,
                created_by=actor_id,
                updated_by=actor_id,
            )
        else:
            resolved_server, assign_source, rule_id = self.resolve_user_server(user.id, preferred_server_id=payload.server_id)
            account.server_id = resolved_server.id if resolved_server else account.server_id
            account.status = "enabled"
            account.assign_source = assign_source
            account.assignment_rule_id = rule_id
            if payload.vpn_username:
                account.vpn_username = payload.vpn_username
            if payload.remark is not None:
                account.remark = payload.remark
            account.updated_by = actor_id
        if not account.server_id:
            raise ConflictError("没有可用的OpenVPN服务器")
        return self.commit(account, "OpenVPN账号已存在")

    def disable_account(self, user_id: int, actor_id: int, status: str = "disabled") -> OpenVpnAccount:
        account = self.get_account_by_user_required(user_id)
        account.status = status
        account.updated_by = actor_id
        self._close_online_sessions(account.id, "账号已禁用")
        return self.commit(account, "OpenVPN账号禁用失败")

    def assign_account_server(self, account_id: int, server_id: Optional[int], actor_id: int) -> OpenVpnAccount:
        account = self.get_account_required(account_id)
        if server_id:
            server = self.get_server_required(server_id)
            account.server_id = server.id
            account.assign_source = "manual"
            account.assignment_rule_id = None
        else:
            server, source, rule_id = self.resolve_user_server(account.user_id)
            if not server:
                raise ConflictError("没有可用的OpenVPN服务器")
            account.server_id = server.id
            account.assign_source = source
            account.assignment_rule_id = rule_id
        account.config_version += 1
        account.updated_by = actor_id
        return self.commit(account, "OpenVPN账号分配服务器失败")

    def get_account_required(self, account_id: int) -> OpenVpnAccount:
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == account_id).first()
        if not account:
            raise NotFoundError("OpenVPN账号不存在")
        return account

    def get_account_by_user_required(self, user_id: int) -> OpenVpnAccount:
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.user_id == user_id).first()
        if not account:
            raise NotFoundError("OpenVPN账号不存在")
        return account

    def issue_certificate(self, account_id: int, expires_at: datetime, actor_id: int) -> OpenVpnCertificate:
        account = self.get_account_required(account_id)
        if account.status != "enabled":
            raise ConflictError("OpenVPN账号未启用")
        if not account.server_id:
            raise ConflictError("OpenVPN账号未分配服务器")
        server = self.get_server_required(account.server_id)
        certificate = OpenVpnCertificate(
            account_id=account.id,
            server_id=server.id,
            common_name=account.vpn_username,
            serial_number=uuid4().hex,
            status="issued",
            expires_at=expires_at,
            created_by=actor_id,
        )
        account.config_version += 1
        account.updated_by = actor_id
        self.db.add(account)
        return self.commit(certificate, "OpenVPN证书签发失败")

    def revoke_certificate(self, certificate_id: int, reason: Optional[str], actor_id: int) -> OpenVpnCertificate:
        certificate = self.get_certificate_required(certificate_id)
        certificate.status = "revoked"
        certificate.revoked_at = datetime.utcnow()
        certificate.revoked_reason = reason
        account = self.get_account_required(certificate.account_id)
        account.config_version += 1
        account.updated_by = actor_id
        self.db.add(account)
        return self.commit(certificate, "OpenVPN证书吊销失败")

    def renew_certificate(self, certificate_id: int, expires_at: datetime, actor_id: int) -> OpenVpnCertificate:
        old_certificate = self.get_certificate_required(certificate_id)
        if old_certificate.status == "revoked":
            raise ConflictError("已吊销证书不能续期")
        old_certificate.status = "expired"
        new_certificate = OpenVpnCertificate(
            account_id=old_certificate.account_id,
            server_id=old_certificate.server_id,
            common_name=old_certificate.common_name,
            serial_number=uuid4().hex,
            status="issued",
            expires_at=expires_at,
            created_by=actor_id,
        )
        account = self.get_account_required(old_certificate.account_id)
        account.config_version += 1
        account.updated_by = actor_id
        self.db.add(old_certificate)
        self.db.add(account)
        return self.commit(new_certificate, "OpenVPN证书续期失败")

    def list_certificates(
        self,
        skip: int = 0,
        limit: int = 100,
        account_id: Optional[int] = None,
        server_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[OpenVpnCertificate]:
        query = self.db.query(OpenVpnCertificate)
        if account_id:
            query = query.filter(OpenVpnCertificate.account_id == account_id)
        if server_id:
            query = query.filter(OpenVpnCertificate.server_id == server_id)
        if status:
            query = query.filter(OpenVpnCertificate.status == status)
        return query.order_by(OpenVpnCertificate.id.desc()).offset(skip).limit(limit).all()

    def get_certificate_required(self, certificate_id: int) -> OpenVpnCertificate:
        certificate = self.db.query(OpenVpnCertificate).filter(OpenVpnCertificate.id == certificate_id).first()
        if not certificate:
            raise NotFoundError("OpenVPN证书不存在")
        return certificate

    def generate_config(self, account_id: int, actor_id: int) -> tuple[str, str]:
        account = self.get_account_required(account_id)
        if account.status != "enabled":
            raise ConflictError("OpenVPN账号未启用")
        if not account.server_id:
            raise ConflictError("OpenVPN账号未分配服务器")
        server = self.get_server_required(account.server_id)
        certificate = (
            self.db.query(OpenVpnCertificate)
            .filter(
                OpenVpnCertificate.account_id == account.id,
                OpenVpnCertificate.server_id == server.id,
                OpenVpnCertificate.status == "issued",
            )
            .order_by(OpenVpnCertificate.expires_at.desc())
            .first()
        )
        if not certificate:
            raise ConflictError("请先签发OpenVPN证书")
        template = server.config_template or self._default_config_template()
        content = template.format(
            host=server.host,
            port=server.port,
            protocol=server.protocol,
            common_name=certificate.common_name,
            serial_number=certificate.serial_number,
        )
        account.last_config_generated_at = datetime.utcnow()
        account.config_version += 1
        account.updated_by = actor_id
        self.commit(account, "OpenVPN配置生成失败")
        return f"{account.vpn_username}-{server.code}.ovpn", content

    def list_sessions(
        self,
        skip: int = 0,
        limit: int = 100,
        server_id: Optional[int] = None,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[OpenVpnSession]:
        query = self.db.query(OpenVpnSession)
        if server_id:
            query = query.filter(OpenVpnSession.server_id == server_id)
        if user_id:
            query = query.filter(OpenVpnSession.user_id == user_id)
        if status:
            query = query.filter(OpenVpnSession.status == status)
        return query.order_by(OpenVpnSession.connected_at.desc()).offset(skip).limit(limit).all()

    def kick_session(self, session_id: int) -> OpenVpnSession:
        session = self.db.query(OpenVpnSession).filter(OpenVpnSession.id == session_id).first()
        if not session:
            raise NotFoundError("OpenVPN会话不存在")
        session.status = "offline"
        session.disconnected_at = datetime.utcnow()
        self.db.add(
            OpenVpnConnectionLog(
                server_id=session.server_id,
                account_id=session.account_id,
                user_id=session.user_id,
                action="kicked",
                real_ip=session.real_ip,
                virtual_ip=session.virtual_ip,
                result="success",
                message="管理员强制下线",
            )
        )
        return self.commit(session, "OpenVPN会话下线失败")

    def list_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        server_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> list[OpenVpnConnectionLog]:
        query = self.db.query(OpenVpnConnectionLog)
        if server_id:
            query = query.filter(OpenVpnConnectionLog.server_id == server_id)
        if user_id:
            query = query.filter(OpenVpnConnectionLog.user_id == user_id)
        if action:
            query = query.filter(OpenVpnConnectionLog.action == action)
        return query.order_by(OpenVpnConnectionLog.occurred_at.desc()).offset(skip).limit(limit).all()

    def list_options(self) -> dict:
        users = (
            self.db.query(User)
            .filter(User.is_deleted.is_(False))
            .order_by(User.id.desc())
            .limit(1000)
            .all()
        )
        departments = (
            self.db.query(Department)
            .filter(Department.is_deleted.is_(False))
            .order_by(Department.id.desc())
            .limit(1000)
            .all()
        )
        roles = (
            self.db.query(Role)
            .filter(Role.is_deleted.is_(False))
            .order_by(Role.sort_order.asc(), Role.id.desc())
            .limit(1000)
            .all()
        )
        positions = (
            self.db.query(Position)
            .filter(Position.is_deleted.is_(False))
            .order_by(Position.sort_order.asc(), Position.id.desc())
            .limit(1000)
            .all()
        )
        return {
            "users": [{"id": item.id, "username": item.username, "nickname": item.nickname} for item in users],
            "departments": [{"id": item.id, "name": item.name} for item in departments],
            "roles": [{"id": item.id, "name": item.name} for item in roles],
            "positions": [{"id": item.id, "name": item.name} for item in positions],
        }

    def export_logs_csv(
        self,
        server_id: Optional[int] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> tuple[str, str]:
        rows = self.list_logs(skip=0, limit=10000, server_id=server_id, user_id=user_id, action=action)
        lines = ["ID,用户ID,服务器ID,动作,结果,VPN IP,公网IP,发生时间,详情"]
        for row in rows:
            values = [
                row.id,
                row.user_id or "",
                row.server_id or "",
                row.action,
                row.result,
                row.virtual_ip or "",
                row.real_ip or "",
                row.occurred_at.isoformat() if row.occurred_at else "",
                (row.message or "").replace('"', '""'),
            ]
            lines.append(",".join(f'"{value}"' for value in values))
        return "openvpn-logs.csv", "\n".join(lines)

    def resolve_user_server(self, user_id: int, preferred_server_id: Optional[int] = None):
        if preferred_server_id:
            return self.get_server_required(preferred_server_id), "manual", None

        target_sets = self._collect_user_targets(user_id)
        for target_type in ("user", "department", "role", "position"):
            target_ids = target_sets[target_type]
            if not target_ids:
                continue
            rule = (
                self.db.query(OpenVpnAssignmentRule)
                .join(OpenVpnServer, OpenVpnServer.id == OpenVpnAssignmentRule.server_id)
                .filter(
                    OpenVpnAssignmentRule.target_type == target_type,
                    OpenVpnAssignmentRule.target_id.in_(target_ids),
                    OpenVpnAssignmentRule.is_active.is_(True),
                    OpenVpnServer.is_deleted.is_(False),
                    OpenVpnServer.is_active.is_(True),
                )
                .order_by(OpenVpnAssignmentRule.priority.asc(), OpenVpnAssignmentRule.created_at.asc())
                .first()
            )
            if rule:
                if rule.server.status in ("online", "offline") or rule.fallback_enabled:
                    return rule.server, target_type, rule.id

        default_server = (
            self.db.query(OpenVpnServer)
            .filter(
                OpenVpnServer.is_default.is_(True),
                OpenVpnServer.is_deleted.is_(False),
                OpenVpnServer.is_active.is_(True),
            )
            .first()
        )
        return default_server, "default", None

    def disable_user_vpn(self, user_id: int, actor_id: int) -> Optional[OpenVpnAccount]:
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.user_id == user_id).first()
        if not account:
            return None
        account.status = "disabled"
        account.updated_by = actor_id
        self._close_online_sessions(account.id, "用户已禁用或删除")
        return self.commit(account, "OpenVPN账号禁用失败")

    def _clear_default_server(self, except_id: Optional[int] = None) -> None:
        query = self.db.query(OpenVpnServer).filter(OpenVpnServer.is_default.is_(True))
        if except_id:
            query = query.filter(OpenVpnServer.id != except_id)
        query.update({OpenVpnServer.is_default: False}, synchronize_session=False)

    def _collect_user_targets(self, user_id: int) -> dict[str, list[int]]:
        department_ids = [row[0] for row in self.db.query(UserDepartment.department_id).filter(UserDepartment.user_id == user_id)]
        role_ids = [row[0] for row in self.db.query(UserRole.role_id).filter(UserRole.user_id == user_id)]
        position_ids = [row[0] for row in self.db.query(UserPosition.position_id).filter(UserPosition.user_id == user_id)]
        return {
            "user": [user_id],
            "department": department_ids,
            "role": role_ids,
            "position": position_ids,
        }

    def _ensure_rule_target_exists(self, target_type: str, target_id: int) -> None:
        model_map = {
            "user": User,
            "department": Department,
            "role": Role,
            "position": Position,
        }
        model = model_map[target_type]
        exists = self.db.query(model.id).filter(model.id == target_id).first()
        if not exists:
            raise NotFoundError("OpenVPN分配对象不存在")

    def _get_active_user_required(self, user_id: int) -> User:
        user = (
            self.db.query(User)
            .filter(User.id == user_id, User.is_deleted.is_(False), User.is_active.is_(True))
            .first()
        )
        if not user:
            raise NotFoundError("用户不存在或未启用")
        return user

    def _close_online_sessions(self, account_id: int, message: str) -> None:
        sessions = (
            self.db.query(OpenVpnSession)
            .filter(OpenVpnSession.account_id == account_id, OpenVpnSession.status == "online")
            .all()
        )
        for session in sessions:
            session.status = "offline"
            session.disconnected_at = datetime.utcnow()
            self.db.add(session)
            self.db.add(
                OpenVpnConnectionLog(
                    server_id=session.server_id,
                    account_id=session.account_id,
                    user_id=session.user_id,
                    action="kicked",
                    real_ip=session.real_ip,
                    virtual_ip=session.virtual_ip,
                    result="success",
                    message=message,
                )
            )

    @staticmethod
    def _default_config_template() -> str:
        return """client
dev tun
proto {protocol}
remote {host} {port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verb 3

# common_name: {common_name}
# certificate_serial: {serial_number}
"""
