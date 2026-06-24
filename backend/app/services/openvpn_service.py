from __future__ import annotations

import base64
from datetime import date, datetime
import ipaddress
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from typing import Optional
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..config import settings
from ..models.department import Department
from ..models.openvpn import (
    OpenVpnAccount,
    OpenVpnAssignmentRule,
    OpenVpnCertificate,
    OpenVpnConnectionLog,
    OpenVpnServer,
    OpenVpnSession,
    OpenVpnTrafficAggregate,
    OpenVpnTrafficAlert,
    OpenVpnTrafficRecord,
    OpenVpnTrafficThresholdRule,
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
    OpenVpnTrafficThresholdRuleCreate,
    OpenVpnTrafficThresholdRuleUpdate,
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
        data = self._apply_server_defaults(payload.model_dump())
        data = self._persist_server_ssh_private_key(data)
        server = OpenVpnServer(**data, created_by=actor_id, updated_by=actor_id)
        self._initialize_server_remote_config(server)
        if server.is_default:
            self._clear_default_server()
        return self.commit(server, "OpenVPN服务器名称或编码已存在")

    def update_server(self, server_id: int, payload: OpenVpnServerUpdate, actor_id: int) -> OpenVpnServer:
        server = self.get_server_required(server_id, include_deleted=True)
        update_data = payload.model_dump(exclude_unset=True)
        should_initialize_remote = self._should_initialize_remote_config(update_data)
        update_data = self._persist_server_ssh_private_key(update_data, server)
        for field_name, value in update_data.items():
            setattr(server, field_name, value)
        self._apply_server_defaults_to_instance(server)
        if should_initialize_remote:
            self._initialize_server_remote_config(server)
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
        if server.vpn_type == "wireguard":
            try:
                public_key = self._wireguard_server_public_key(server)
            except ConflictError as error:
                return {"ok": False, "message": str(error)}
            return {"ok": True, "message": "WireGuard服务器配置可用", "public_key": public_key}
        if server.certificate_backend == "local_easyrsa":
            if not server.easy_rsa_dir:
                return {"ok": False, "message": "未配置Easy-RSA目录"}
            easy_rsa_dir = Path(server.easy_rsa_dir).expanduser()
            executable = easy_rsa_dir / "easyrsa"
            if not executable.exists():
                return {"ok": False, "message": f"Easy-RSA执行文件不存在：{executable}"}
            pki_dir = self._server_pki_dir(server)
            ca_path = Path(server.ca_cert_path).expanduser() if server.ca_cert_path else pki_dir / "ca.crt"
            tls_key_path = Path(server.tls_crypt_key_path).expanduser() if server.tls_crypt_key_path else None
            if not pki_dir.exists():
                return {"ok": False, "message": f"PKI目录不存在：{pki_dir}"}
            if not ca_path.exists():
                return {"ok": False, "message": f"CA证书不存在：{ca_path}"}
            if tls_key_path and not tls_key_path.exists():
                return {"ok": False, "message": f"TLS密钥不存在：{tls_key_path}"}
            return {"ok": True, "message": "Easy-RSA证书后端配置可用"}
        if server.certificate_backend == "ssh_easyrsa":
            try:
                self._run_remote_shell(server, self._remote_test_command(server))
            except ConflictError as error:
                return {"ok": False, "message": str(error)}
            return {"ok": True, "message": "远程Easy-RSA证书后端配置可用"}
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
            account.config_version += 1
            if not account.vpn_username:
                account.vpn_username = user.username
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

    def revoke_account(self, account_id: int, reason: Optional[str], actor_id: int) -> OpenVpnAccount:
        account = self.get_account_required(account_id)
        certificate = (
            self.db.query(OpenVpnCertificate)
            .filter(
                OpenVpnCertificate.account_id == account.id,
                OpenVpnCertificate.status == "issued",
            )
            .order_by(OpenVpnCertificate.expires_at.desc(), OpenVpnCertificate.id.desc())
            .first()
        )
        if certificate:
            server = self.get_server_required(certificate.server_id)
            if server.vpn_type == "wireguard":
                self._revoke_wireguard_peer(server, account)
            else:
                self._revoke_certificate_files(server, certificate.common_name)
            certificate.status = "revoked"
            certificate.revoked_at = datetime.utcnow()
            certificate.revoked_reason = reason or "账号吊销"
            self.db.add(certificate)

        account.status = "revoked"
        account.config_version += 1
        account.updated_by = actor_id
        self._close_online_sessions(account.id, "账号已吊销")
        self._delete_account_certificate_files(account)
        return self.commit(account, "OpenVPN账号吊销失败")

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
        existing = (
            self.db.query(OpenVpnCertificate)
            .filter(
                OpenVpnCertificate.account_id == account.id,
                OpenVpnCertificate.server_id == server.id,
                OpenVpnCertificate.status == "issued",
            )
            .first()
        )
        if existing:
            raise ConflictError("该账号已有有效VPN凭据，请使用续期或先吊销")
        cert_info = (
            self._issue_wireguard_peer(server, account)
            if server.vpn_type == "wireguard"
            else self._issue_certificate_files(server, account.vpn_username, expires_at)
        )
        cert_info = self._archive_certificate_files(server, account, cert_info)
        certificate = OpenVpnCertificate(
            account_id=account.id,
            server_id=server.id,
            common_name=account.vpn_username,
            serial_number=cert_info["serial_number"],
            status="issued",
            expires_at=expires_at,
            cert_path=cert_info.get("cert_path"),
            key_path=cert_info.get("key_path"),
            request_path=cert_info.get("request_path"),
            created_by=actor_id,
        )
        account.config_version += 1
        account.updated_by = actor_id
        self.db.add(account)
        return self.commit(certificate, "OpenVPN证书签发失败")

    def revoke_certificate(self, certificate_id: int, reason: Optional[str], actor_id: int) -> OpenVpnCertificate:
        certificate = self.get_certificate_required(certificate_id)
        if certificate.status == "revoked":
            return certificate
        server = self.get_server_required(certificate.server_id)
        if server.vpn_type == "wireguard":
            account = self.get_account_required(certificate.account_id)
            self._revoke_wireguard_peer(server, account)
        else:
            self._revoke_certificate_files(server, certificate.common_name)
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
        server = self.get_server_required(old_certificate.server_id)
        if server.vpn_type == "wireguard":
            old_certificate.expires_at = expires_at
            account = self.get_account_required(old_certificate.account_id)
            account.config_version += 1
            account.updated_by = actor_id
            self.db.add(account)
            return self.commit(old_certificate, "WireGuard凭据续期失败")
        old_certificate.status = "expired"
        account = self.get_account_required(old_certificate.account_id)
        cert_info = self._renew_certificate_files(server, old_certificate.common_name, expires_at)
        cert_info = self._archive_certificate_files(server, account, cert_info)
        new_certificate = OpenVpnCertificate(
            account_id=old_certificate.account_id,
            server_id=old_certificate.server_id,
            common_name=old_certificate.common_name,
            serial_number=cert_info["serial_number"],
            status="issued",
            expires_at=expires_at,
            cert_path=cert_info.get("cert_path"),
            key_path=cert_info.get("key_path"),
            request_path=cert_info.get("request_path"),
            created_by=actor_id,
        )
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
            raise ConflictError("请先签发VPN凭据")
        content = self._render_client_config(server, certificate)
        account.last_config_generated_at = datetime.utcnow()
        account.config_version += 1
        account.updated_by = actor_id
        filename = f"{self._account_certificate_basename(server, account)}.{self._client_config_extension(server)}"
        if server.client_config_dir:
            config_path = self._account_certificate_dir(server, account) / filename
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(content, encoding="utf-8")
            certificate.config_file_path = str(config_path)
            self.db.add(certificate)
        self.commit(account, "VPN配置生成失败")
        return filename, content

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

    def record_session_connect(self, payload) -> OpenVpnSession:
        server = self._resolve_event_server(payload)
        account = self._find_account_by_common_name(payload.common_name)
        now = datetime.utcnow()
        connected_at = payload.connected_at or now
        real_ip = payload.real_ip or payload.trusted_ip

        existing_sessions = (
            self.db.query(OpenVpnSession)
            .filter(
                OpenVpnSession.server_id == server.id,
                OpenVpnSession.common_name == payload.common_name,
                OpenVpnSession.status == "online",
            )
            .all()
        )
        for item in existing_sessions:
            item.status = "offline"
            item.disconnected_at = connected_at
            self.db.add(item)

        session = OpenVpnSession(
            server_id=server.id,
            account_id=account.id if account else None,
            user_id=account.user_id if account else None,
            common_name=payload.common_name,
            virtual_ip=payload.virtual_ip,
            real_ip=real_ip,
            connected_at=connected_at,
            bytes_in=payload.bytes_in or 0,
            bytes_out=payload.bytes_out or 0,
            status="online",
        )
        server.current_clients = self._server_online_session_count(server.id) + 1
        if account:
            account.last_connected_at = connected_at
            account.last_virtual_ip = payload.virtual_ip
            account.last_real_ip = real_ip
            self.db.add(account)
        self.db.add(server)
        self.db.add(
            OpenVpnConnectionLog(
                server_id=server.id,
                account_id=account.id if account else None,
                user_id=account.user_id if account else None,
                action="connected",
                real_ip=real_ip,
                virtual_ip=payload.virtual_ip,
                result="success",
                message=payload.message or "客户端连接",
                extra={"common_name": payload.common_name},
            )
        )
        return self.commit(session, "OpenVPN连接事件记录失败")

    def record_session_disconnect(self, payload) -> OpenVpnSession:
        server = self._resolve_event_server(payload)
        account = self._find_account_by_common_name(payload.common_name)
        disconnected_at = payload.disconnected_at or datetime.utcnow()
        real_ip = payload.real_ip or payload.trusted_ip
        session = (
            self.db.query(OpenVpnSession)
            .filter(
                OpenVpnSession.server_id == server.id,
                OpenVpnSession.common_name == payload.common_name,
                OpenVpnSession.status == "online",
            )
            .order_by(OpenVpnSession.connected_at.desc(), OpenVpnSession.id.desc())
            .first()
        )
        if not session:
            session = OpenVpnSession(
                server_id=server.id,
                account_id=account.id if account else None,
                user_id=account.user_id if account else None,
                common_name=payload.common_name,
                virtual_ip=payload.virtual_ip,
                real_ip=real_ip,
                connected_at=disconnected_at,
                status="offline",
            )
        session.status = "offline"
        session.disconnected_at = disconnected_at
        session.bytes_in = payload.bytes_in or session.bytes_in or 0
        session.bytes_out = payload.bytes_out or session.bytes_out or 0
        if payload.virtual_ip:
            session.virtual_ip = payload.virtual_ip
        if real_ip:
            session.real_ip = real_ip

        self.db.add(session)
        self.db.flush()
        self._record_session_traffic(session)

        server.current_clients = self._server_online_session_count(server.id)
        self.db.add(server)
        self.db.add(
            OpenVpnConnectionLog(
                server_id=server.id,
                account_id=session.account_id,
                user_id=session.user_id,
                action="disconnected",
                real_ip=session.real_ip,
                virtual_ip=session.virtual_ip,
                result="success",
                message=payload.message or "客户端断开",
                extra={
                    "common_name": payload.common_name,
                    "bytes_in": session.bytes_in,
                    "bytes_out": session.bytes_out,
                },
            )
        )
        return self.commit(session, "OpenVPN断开事件记录失败")

    def kick_session(self, session_id: int) -> OpenVpnSession:
        session = self.db.query(OpenVpnSession).filter(OpenVpnSession.id == session_id).first()
        if not session:
            raise NotFoundError("OpenVPN会话不存在")
        if session.status != "online":
            raise ConflictError("只有在线会话可以强制下线")
        session.status = "offline"
        session.disconnected_at = datetime.utcnow()
        server = self.get_server_required(session.server_id, include_deleted=True)
        server.current_clients = self._server_online_session_count(server.id)
        self.db.add(server)
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
        cursor_id: Optional[int] = None,
    ) -> list[OpenVpnConnectionLog]:
        query = self.db.query(OpenVpnConnectionLog)
        if server_id:
            query = query.filter(OpenVpnConnectionLog.server_id == server_id)
        if user_id:
            query = query.filter(OpenVpnConnectionLog.user_id == user_id)
        if action:
            query = query.filter(OpenVpnConnectionLog.action == action)
        if cursor_id:
            query = query.filter(OpenVpnConnectionLog.id < cursor_id)
            skip = 0
        return query.order_by(OpenVpnConnectionLog.id.desc()).offset(skip).limit(limit).all()

    def list_options(self) -> dict:
        users = (
            self.db.query(User)
            .filter(
                User.is_deleted.is_(False),
                User.is_active.is_(True),
                ~User.id.in_(
                    self.db.query(OpenVpnAccount.user_id).filter(OpenVpnAccount.status != "revoked")
                ),
            )
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
        user_department_rows = self.db.query(UserDepartment.user_id, UserDepartment.department_id).all()
        user_department_map = {}
        for user_id, department_id in user_department_rows:
            user_department_map.setdefault(user_id, []).append(department_id)
        return {
            "users": [
                {
                    "id": item.id,
                    "username": item.username,
                    "nickname": item.nickname,
                    "department_ids": user_department_map.get(item.id, []),
                }
                for item in users
            ],
            "departments": [{"id": item.id, "name": item.name, "code": item.code, "parent_id": item.parent_id} for item in departments],
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

    def traffic_overview(
        self,
        period_type: str = "day",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        query = self._traffic_aggregate_query(period_type, "server", date_from, date_to)
        totals = query.with_entities(
            func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_in), 0),
            func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_out), 0),
            func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_total), 0),
            func.coalesce(func.sum(OpenVpnTrafficAggregate.session_count), 0),
        ).first()
        return {
            "bytes_in": int(totals[0] or 0),
            "bytes_out": int(totals[1] or 0),
            "bytes_total": int(totals[2] or 0),
            "session_count": int(totals[3] or 0),
            "open_alert_count": self.db.query(OpenVpnTrafficAlert).filter(OpenVpnTrafficAlert.status == "open").count(),
            "active_rule_count": self.db.query(OpenVpnTrafficThresholdRule).filter(OpenVpnTrafficThresholdRule.is_active.is_(True)).count(),
        }

    def traffic_distribution(
        self,
        dimension: str,
        period_type: str = "day",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[dict]:
        self._validate_traffic_dimension(dimension)
        rows = (
            self._traffic_aggregate_query(period_type, dimension, date_from, date_to)
            .with_entities(
                OpenVpnTrafficAggregate.dimension_id,
                func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_out), 0),
                func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_total), 0),
                func.coalesce(func.sum(OpenVpnTrafficAggregate.session_count), 0),
            )
            .group_by(OpenVpnTrafficAggregate.dimension_id)
            .order_by(func.sum(OpenVpnTrafficAggregate.bytes_total).desc())
            .all()
        )
        names = self._traffic_dimension_names(dimension, [row[0] for row in rows if row[0]])
        return [self._traffic_metric_item(dimension, row, names) for row in rows]

    def traffic_ranking(
        self,
        dimension: str,
        period_type: str = "day",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 10,
    ) -> list[dict]:
        return self.traffic_distribution(dimension, period_type, date_from, date_to)[: max(1, min(limit, 100))]

    def traffic_trend(
        self,
        period_type: str = "day",
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        dimension: Optional[str] = None,
        target_id: Optional[int] = None,
    ) -> list[dict]:
        self._validate_traffic_period(period_type)
        query = self.db.query(OpenVpnTrafficAggregate).filter(OpenVpnTrafficAggregate.period_type == period_type)
        if dimension:
            self._validate_traffic_dimension(dimension)
            query = query.filter(OpenVpnTrafficAggregate.dimension_type == dimension)
            if target_id:
                query = query.filter(OpenVpnTrafficAggregate.dimension_id == target_id)
        else:
            query = query.filter(OpenVpnTrafficAggregate.dimension_type == "server")
        query = self._apply_traffic_date_range(query, date_from, date_to)
        rows = (
            query.with_entities(
                OpenVpnTrafficAggregate.period_start,
                func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_in), 0),
                func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_out), 0),
                func.coalesce(func.sum(OpenVpnTrafficAggregate.bytes_total), 0),
                func.coalesce(func.sum(OpenVpnTrafficAggregate.session_count), 0),
            )
            .group_by(OpenVpnTrafficAggregate.period_start)
            .order_by(OpenVpnTrafficAggregate.period_start.asc())
            .all()
        )
        return [
            {
                "period_start": row[0],
                "bytes_in": int(row[1] or 0),
                "bytes_out": int(row[2] or 0),
                "bytes_total": int(row[3] or 0),
                "session_count": int(row[4] or 0),
            }
            for row in rows
        ]

    def list_traffic_threshold_rules(
        self,
        skip: int = 0,
        limit: int = 100,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> list[OpenVpnTrafficThresholdRule]:
        query = self.db.query(OpenVpnTrafficThresholdRule)
        if target_type:
            query = query.filter(OpenVpnTrafficThresholdRule.target_type == target_type)
        if target_id:
            query = query.filter(OpenVpnTrafficThresholdRule.target_id == target_id)
        if is_active is not None:
            query = query.filter(OpenVpnTrafficThresholdRule.is_active.is_(is_active))
        return query.order_by(OpenVpnTrafficThresholdRule.id.desc()).offset(skip).limit(limit).all()

    def create_traffic_threshold_rule(
        self,
        payload: OpenVpnTrafficThresholdRuleCreate,
        actor_id: int,
    ) -> OpenVpnTrafficThresholdRule:
        self._ensure_traffic_threshold_target_exists(payload.target_type, payload.target_id)
        rule = OpenVpnTrafficThresholdRule(**payload.model_dump(), created_by=actor_id, updated_by=actor_id)
        return self.commit(rule, "OpenVPN流量阈值规则已存在")

    def update_traffic_threshold_rule(
        self,
        rule_id: int,
        payload: OpenVpnTrafficThresholdRuleUpdate,
        actor_id: int,
    ) -> OpenVpnTrafficThresholdRule:
        rule = self.get_traffic_threshold_rule_required(rule_id)
        update_data = payload.model_dump(exclude_unset=True)
        target_type = update_data.get("target_type", rule.target_type)
        target_id = update_data.get("target_id", rule.target_id)
        if "target_type" in update_data or "target_id" in update_data:
            self._ensure_traffic_threshold_target_exists(target_type, target_id)
        for field_name, value in update_data.items():
            setattr(rule, field_name, value)
        rule.updated_by = actor_id
        return self.commit(rule, "OpenVPN流量阈值规则已存在")

    def delete_traffic_threshold_rule(self, rule_id: int) -> OpenVpnTrafficThresholdRule:
        rule = self.get_traffic_threshold_rule_required(rule_id)
        self.db.delete(rule)
        self.db.commit()
        return rule

    def get_traffic_threshold_rule_required(self, rule_id: int) -> OpenVpnTrafficThresholdRule:
        rule = self.db.query(OpenVpnTrafficThresholdRule).filter(OpenVpnTrafficThresholdRule.id == rule_id).first()
        if not rule:
            raise NotFoundError("OpenVPN流量阈值规则不存在")
        return rule

    def list_traffic_alerts(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[int] = None,
    ) -> list[OpenVpnTrafficAlert]:
        query = self.db.query(OpenVpnTrafficAlert)
        if status:
            query = query.filter(OpenVpnTrafficAlert.status == status)
        if target_type:
            query = query.filter(OpenVpnTrafficAlert.target_type == target_type)
        if target_id:
            query = query.filter(OpenVpnTrafficAlert.target_id == target_id)
        return query.order_by(OpenVpnTrafficAlert.created_at.desc()).offset(skip).limit(limit).all()

    def process_traffic_alert(self, alert_id: int, note: Optional[str], actor_id: int) -> OpenVpnTrafficAlert:
        alert = self.db.query(OpenVpnTrafficAlert).filter(OpenVpnTrafficAlert.id == alert_id).first()
        if not alert:
            raise NotFoundError("OpenVPN流量告警不存在")
        alert.status = "processed"
        alert.processed_by = actor_id
        alert.processed_at = datetime.utcnow()
        alert.process_note = note
        return self.commit(alert, "OpenVPN流量告警处理失败")

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

    def _apply_server_defaults(self, data: dict) -> dict:
        vpn_type = data.get("vpn_type") or "openvpn"
        data["vpn_type"] = vpn_type
        if vpn_type == "wireguard":
            data["port"] = data.get("port") or 51820
            data["protocol"] = data.get("protocol") or "udp"
            data["certificate_backend"] = "wireguard"
            data["ssh_host"] = data.get("ssh_host") or data.get("host")
            data["ssh_port"] = data.get("ssh_port") or 22
            data["ssh_user"] = data.get("ssh_user") or "root"
            data["ssh_key_path"] = data.get("ssh_key_path") or self._default_server_ssh_key_path(data.get("code"))
            data["wg_interface"] = data.get("wg_interface") or "wg0"
            data["wg_network_cidr"] = data.get("wg_network_cidr") or "10.66.0.0/24"
            data["wg_dns"] = data.get("wg_dns") or "1.1.1.1,1.0.0.1"
            data["wg_allowed_ips"] = data.get("wg_allowed_ips") or "0.0.0.0/0,::/0"
            data["wg_persistent_keepalive"] = data.get("wg_persistent_keepalive") if data.get("wg_persistent_keepalive") is not None else 25
            data["client_config_dir"] = data.get("client_config_dir") or settings.openvpn_client_config_root
            return data
        backend = data.get("certificate_backend") or "metadata"
        if backend in ("ssh_easyrsa", "local_easyrsa"):
            easy_rsa_dir = (data.get("easy_rsa_dir") or settings.openvpn_default_easy_rsa_dir).rstrip("/")
            pki_dir = (data.get("pki_dir") or f"{easy_rsa_dir}/pki").rstrip("/")
            data["easy_rsa_dir"] = easy_rsa_dir
            data["pki_dir"] = pki_dir
            data["ca_cert_path"] = data.get("ca_cert_path") or f"{pki_dir}/ca.crt"
            data["crl_path"] = data.get("crl_path") or f"{pki_dir}/crl.pem"
            data["tls_crypt_key_path"] = data.get("tls_crypt_key_path") or settings.openvpn_default_tls_crypt_key_path
            data["client_config_dir"] = data.get("client_config_dir") or settings.openvpn_client_config_root
        if backend == "ssh_easyrsa":
            data["ssh_host"] = data.get("ssh_host") or data.get("host")
            data["ssh_port"] = data.get("ssh_port") or 22
            data["ssh_key_path"] = data.get("ssh_key_path") or self._default_server_ssh_key_path(data.get("code"))
        return data

    def _persist_server_ssh_private_key(self, data: dict, server: Optional[OpenVpnServer] = None) -> dict:
        private_key_content = (data.pop("ssh_private_key_content", None) or "").strip()
        if not private_key_content:
            return data

        if "BEGIN OPENSSH PRIVATE KEY" not in private_key_content and "BEGIN RSA PRIVATE KEY" not in private_key_content:
            raise ConflictError("SSH私钥内容格式不正确，请填写完整私钥内容")

        key_path_value = data.get("ssh_key_path") or (server.ssh_key_path if server else None)
        if not key_path_value or str(key_path_value).startswith("/Users/"):
            key_name = self._safe_path_segment(data.get("code") or (server.code if server else "openvpn_server"))
            default_root = Path(settings.openvpn_ssh_key_dir).expanduser()
            key_path = default_root / f"{key_name}.key"
        else:
            key_path = Path(str(key_path_value)).expanduser()

        try:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key_path.write_text(private_key_content.rstrip() + "\n", encoding="utf-8")
            key_path.chmod(0o600)
        except OSError as exc:
            raise ConflictError(f"SSH私钥写入失败：{key_path}，请检查后端容器挂载目录权限：{exc}") from exc

        data["ssh_key_path"] = str(key_path)
        return data

    def _should_initialize_remote_config(self, update_data: dict) -> bool:
        remote_fields = {
            "vpn_type",
            "host",
            "port",
            "certificate_backend",
            "ssh_host",
            "ssh_port",
            "ssh_user",
            "ssh_key_path",
            "ssh_private_key_content",
            "easy_rsa_dir",
            "pki_dir",
            "ca_cert_path",
            "tls_crypt_key_path",
            "wg_interface",
            "wg_network_cidr",
            "wg_dns",
            "wg_allowed_ips",
            "wg_public_key",
        }
        return bool(remote_fields.intersection(update_data.keys()))

    def _initialize_server_remote_config(self, server: OpenVpnServer) -> None:
        if not self._server_uses_ssh(server):
            return
        self._ensure_server_ssh_key_available(server)
        if server.vpn_type == "wireguard":
            server.wg_public_key = self._wireguard_server_public_key(server)
            return
        if server.certificate_backend == "ssh_easyrsa":
            self._run_remote_shell(server, self._remote_test_command(server))

    @staticmethod
    def _server_uses_ssh(server: OpenVpnServer) -> bool:
        return server.vpn_type == "wireguard" or server.certificate_backend == "ssh_easyrsa"

    def _ensure_server_ssh_key_available(self, server: OpenVpnServer) -> None:
        key_path_value = self._effective_ssh_key_path(server)
        if not key_path_value:
            raise ConflictError("服务器需要SSH连接，请填写SSH私钥内容后保存")
        key_path = Path(key_path_value).expanduser()
        if not key_path.exists():
            raise ConflictError(
                f"SSH私钥文件不存在：{key_path}。请在添加/编辑VPN服务器时填写SSH私钥内容，"
                f"系统会自动写入 /data/oim/ssh/{server.code}.key 并设置权限"
            )
        if not key_path.is_file():
            raise ConflictError(f"SSH私钥路径不是文件：{key_path}")

    def _apply_server_defaults_to_instance(self, server: OpenVpnServer) -> None:
        data = self._apply_server_defaults(
            {
                "certificate_backend": server.certificate_backend,
                "vpn_type": server.vpn_type,
                "code": server.code,
                "host": server.host,
                "ssh_host": server.ssh_host,
                "ssh_port": server.ssh_port,
                "ssh_key_path": server.ssh_key_path,
                "easy_rsa_dir": server.easy_rsa_dir,
                "pki_dir": server.pki_dir,
                "ca_cert_path": server.ca_cert_path,
                "tls_crypt_key_path": server.tls_crypt_key_path,
                "crl_path": server.crl_path,
                "client_config_dir": server.client_config_dir,
                "wg_interface": server.wg_interface,
                "wg_network_cidr": server.wg_network_cidr,
                "wg_dns": server.wg_dns,
                "wg_allowed_ips": server.wg_allowed_ips,
                "wg_persistent_keepalive": server.wg_persistent_keepalive,
                "wg_public_key": server.wg_public_key,
            }
        )
        for field_name, value in data.items():
            if hasattr(server, field_name):
                setattr(server, field_name, value)

    def _default_server_ssh_key_path(self, server_code: Optional[str]) -> Optional[str]:
        if server_code:
            key_name = self._safe_path_segment(server_code)
            return str(Path(settings.openvpn_ssh_key_dir).expanduser() / f"{key_name}.key")
        return settings.openvpn_default_ssh_key_path

    def _clear_default_server(self, except_id: Optional[int] = None) -> None:
        query = self.db.query(OpenVpnServer).filter(OpenVpnServer.is_default.is_(True))
        if except_id:
            query = query.filter(OpenVpnServer.id != except_id)
        query.update({OpenVpnServer.is_default: False}, synchronize_session=False)

    def _resolve_event_server(self, payload) -> OpenVpnServer:
        if payload.server_id:
            return self.get_server_required(payload.server_id, include_deleted=True)
        if payload.server_code:
            server = (
                self.db.query(OpenVpnServer)
                .filter(OpenVpnServer.code == payload.server_code, OpenVpnServer.is_deleted.is_(False))
                .first()
            )
            if server:
                return server
        raise NotFoundError("OpenVPN服务器不存在，请检查事件上报的server_code或server_id")

    def _record_session_traffic(self, session: OpenVpnSession) -> None:
        if session.id and self.db.query(OpenVpnTrafficRecord.id).filter(OpenVpnTrafficRecord.session_id == session.id).first():
            return
        bytes_in = int(session.bytes_in or 0)
        bytes_out = int(session.bytes_out or 0)
        bytes_total = bytes_in + bytes_out
        recorded_at = session.disconnected_at or datetime.utcnow()
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == session.account_id).first() if session.account_id else None
        certificate = self._find_session_certificate(session, account)
        department_id = self._primary_department_id(account.user_id if account else session.user_id)

        record = OpenVpnTrafficRecord(
            server_id=session.server_id,
            account_id=session.account_id,
            certificate_id=certificate.id if certificate else None,
            user_id=session.user_id,
            department_id=department_id,
            session_id=session.id,
            common_name=session.common_name,
            virtual_ip=session.virtual_ip,
            real_ip=session.real_ip,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            bytes_total=bytes_total,
            recorded_at=recorded_at,
        )
        self.db.add(record)

        dimensions = [
            ("server", session.server_id, session.server_id, session.account_id, certificate.id if certificate else None, department_id),
            ("certificate", certificate.id if certificate else None, session.server_id, session.account_id, certificate.id if certificate else None, department_id),
            ("department", department_id, session.server_id, session.account_id, certificate.id if certificate else None, department_id),
        ]
        for period_type, period_start in self._traffic_periods(recorded_at).items():
            for dimension_type, dimension_id, server_id, account_id, certificate_id, agg_department_id in dimensions:
                if not dimension_id:
                    continue
                self._upsert_traffic_aggregate(
                    period_type=period_type,
                    period_start=period_start,
                    dimension_type=dimension_type,
                    dimension_id=dimension_id,
                    server_id=server_id,
                    account_id=account_id,
                    certificate_id=certificate_id,
                    department_id=agg_department_id,
                    bytes_in=bytes_in,
                    bytes_out=bytes_out,
                    bytes_total=bytes_total,
                )
        self._evaluate_traffic_thresholds(recorded_at, session.server_id, certificate)

    def _find_session_certificate(self, session: OpenVpnSession, account: Optional[OpenVpnAccount]) -> Optional[OpenVpnCertificate]:
        query = self.db.query(OpenVpnCertificate).filter(
            OpenVpnCertificate.server_id == session.server_id,
            OpenVpnCertificate.common_name == session.common_name,
        )
        if account:
            query = query.filter(OpenVpnCertificate.account_id == account.id)
        return query.order_by(OpenVpnCertificate.issued_at.desc(), OpenVpnCertificate.id.desc()).first()

    def _primary_department_id(self, user_id: Optional[int]) -> Optional[int]:
        if not user_id:
            return None
        row = (
            self.db.query(UserDepartment.department_id)
            .filter(UserDepartment.user_id == user_id)
            .order_by(UserDepartment.is_primary.desc(), UserDepartment.id.asc())
            .first()
        )
        return row[0] if row else None

    @staticmethod
    def _traffic_periods(value: datetime) -> dict[str, date]:
        current = value.date()
        return {
            "day": current,
            "month": date(current.year, current.month, 1),
        }

    def _upsert_traffic_aggregate(
        self,
        period_type: str,
        period_start: date,
        dimension_type: str,
        dimension_id: int,
        server_id: Optional[int],
        account_id: Optional[int],
        certificate_id: Optional[int],
        department_id: Optional[int],
        bytes_in: int,
        bytes_out: int,
        bytes_total: int,
    ) -> OpenVpnTrafficAggregate:
        aggregate = (
            self.db.query(OpenVpnTrafficAggregate)
            .filter(
                OpenVpnTrafficAggregate.period_type == period_type,
                OpenVpnTrafficAggregate.period_start == period_start,
                OpenVpnTrafficAggregate.dimension_type == dimension_type,
                OpenVpnTrafficAggregate.dimension_id == dimension_id,
            )
            .first()
        )
        if not aggregate:
            aggregate = OpenVpnTrafficAggregate(
                period_type=period_type,
                period_start=period_start,
                dimension_type=dimension_type,
                dimension_id=dimension_id,
                server_id=server_id,
                account_id=account_id,
                certificate_id=certificate_id,
                department_id=department_id,
                bytes_in=0,
                bytes_out=0,
                bytes_total=0,
                session_count=0,
            )
        aggregate.bytes_in = int(aggregate.bytes_in or 0) + bytes_in
        aggregate.bytes_out = int(aggregate.bytes_out or 0) + bytes_out
        aggregate.bytes_total = int(aggregate.bytes_total or 0) + bytes_total
        aggregate.session_count = int(aggregate.session_count or 0) + 1
        aggregate.updated_at = datetime.utcnow()
        self.db.add(aggregate)
        return aggregate

    def _evaluate_traffic_thresholds(
        self,
        recorded_at: datetime,
        server_id: Optional[int],
        certificate: Optional[OpenVpnCertificate],
    ) -> None:
        targets = [("server", server_id)]
        if certificate:
            targets.append(("certificate", certificate.id))
        for target_type, target_id in targets:
            if not target_id:
                continue
            rules = (
                self.db.query(OpenVpnTrafficThresholdRule)
                .filter(
                    OpenVpnTrafficThresholdRule.target_type == target_type,
                    OpenVpnTrafficThresholdRule.target_id == target_id,
                    OpenVpnTrafficThresholdRule.is_active.is_(True),
                )
                .all()
            )
            for rule in rules:
                period_start = self._traffic_periods(recorded_at)[rule.period_type]
                aggregate = (
                    self.db.query(OpenVpnTrafficAggregate)
                    .filter(
                        OpenVpnTrafficAggregate.period_type == rule.period_type,
                        OpenVpnTrafficAggregate.period_start == period_start,
                        OpenVpnTrafficAggregate.dimension_type == target_type,
                        OpenVpnTrafficAggregate.dimension_id == target_id,
                    )
                    .first()
                )
                actual_bytes = int(aggregate.bytes_total or 0) if aggregate else 0
                if actual_bytes <= int(rule.threshold_bytes or 0):
                    continue
                exists = (
                    self.db.query(OpenVpnTrafficAlert.id)
                    .filter(
                        OpenVpnTrafficAlert.rule_id == rule.id,
                        OpenVpnTrafficAlert.period_type == rule.period_type,
                        OpenVpnTrafficAlert.period_start == period_start,
                        OpenVpnTrafficAlert.target_type == target_type,
                        OpenVpnTrafficAlert.target_id == target_id,
                    )
                    .first()
                )
                if exists:
                    continue
                alert = OpenVpnTrafficAlert(
                    rule_id=rule.id,
                    target_type=target_type,
                    target_id=target_id,
                    server_id=server_id if target_type == "server" else certificate.server_id if certificate else None,
                    certificate_id=certificate.id if certificate else None,
                    account_id=certificate.account_id if certificate else None,
                    period_type=rule.period_type,
                    period_start=period_start,
                    threshold_bytes=rule.threshold_bytes,
                    actual_bytes=actual_bytes,
                    action=rule.action,
                    status="open",
                    message=f"OpenVPN流量超过阈值：当前 {actual_bytes} 字节，阈值 {rule.threshold_bytes} 字节",
                )
                self.db.add(alert)
                if rule.action == "disable_certificate" and certificate:
                    self._disable_certificate_by_threshold(certificate, "流量阈值超限自动禁用")

    def _disable_certificate_by_threshold(self, certificate: OpenVpnCertificate, reason: str) -> None:
        if certificate.status == "revoked":
            return
        certificate.status = "revoked"
        certificate.revoked_at = datetime.utcnow()
        certificate.revoked_reason = reason
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == certificate.account_id).first()
        if account:
            account.config_version += 1
            account.updated_at = datetime.utcnow()
            self._close_online_sessions(account.id, reason)
            self.db.add(account)
        self.db.add(certificate)

    def _traffic_aggregate_query(
        self,
        period_type: str,
        dimension: str,
        date_from: Optional[date],
        date_to: Optional[date],
    ):
        self._validate_traffic_period(period_type)
        self._validate_traffic_dimension(dimension)
        query = self.db.query(OpenVpnTrafficAggregate).filter(
            OpenVpnTrafficAggregate.period_type == period_type,
            OpenVpnTrafficAggregate.dimension_type == dimension,
        )
        return self._apply_traffic_date_range(query, date_from, date_to)

    @staticmethod
    def _apply_traffic_date_range(query, date_from: Optional[date], date_to: Optional[date]):
        if date_from:
            query = query.filter(OpenVpnTrafficAggregate.period_start >= date_from)
        if date_to:
            query = query.filter(OpenVpnTrafficAggregate.period_start <= date_to)
        return query

    @staticmethod
    def _validate_traffic_period(period_type: str) -> None:
        if period_type not in {"day", "month"}:
            raise ConflictError("统计周期只能是 day 或 month")

    @staticmethod
    def _validate_traffic_dimension(dimension: str) -> None:
        if dimension not in {"server", "department", "certificate"}:
            raise ConflictError("统计维度只能是 server、department 或 certificate")

    def _traffic_dimension_names(self, dimension: str, ids: list[int]) -> dict[int, str]:
        if not ids:
            return {}
        if dimension == "server":
            rows = self.db.query(OpenVpnServer.id, OpenVpnServer.name).filter(OpenVpnServer.id.in_(ids)).all()
            return {row[0]: row[1] for row in rows}
        if dimension == "department":
            rows = self.db.query(Department.id, Department.name).filter(Department.id.in_(ids)).all()
            return {row[0]: row[1] for row in rows}
        rows = (
            self.db.query(OpenVpnCertificate.id, OpenVpnCertificate.common_name, User.username)
            .join(OpenVpnAccount, OpenVpnAccount.id == OpenVpnCertificate.account_id)
            .join(User, User.id == OpenVpnAccount.user_id)
            .filter(OpenVpnCertificate.id.in_(ids))
            .all()
        )
        return {row[0]: f"{row[2]} / {row[1]}" for row in rows}

    def _traffic_metric_item(self, dimension: str, row, names: dict[int, str]) -> dict:
        dimension_id = row[0]
        return {
            "dimension_type": dimension,
            "dimension_id": dimension_id,
            "name": names.get(dimension_id, "未识别对象" if dimension_id else "未归属"),
            "bytes_in": int(row[1] or 0),
            "bytes_out": int(row[2] or 0),
            "bytes_total": int(row[3] or 0),
            "session_count": int(row[4] or 0),
        }

    def _ensure_traffic_threshold_target_exists(self, target_type: str, target_id: int) -> None:
        if target_type == "server":
            self.get_server_required(target_id, include_deleted=True)
            return
        if target_type == "certificate":
            self.get_certificate_required(target_id)
            return
        raise ConflictError("阈值对象只能是服务器或证书")

    def traffic_target_name(self, target_type: str, target_id: Optional[int]) -> Optional[str]:
        if not target_id:
            return None
        if target_type == "server":
            server = self.db.query(OpenVpnServer).filter(OpenVpnServer.id == target_id).first()
            return server.name if server else None
        if target_type == "certificate":
            certificate = self.db.query(OpenVpnCertificate).filter(OpenVpnCertificate.id == target_id).first()
            if not certificate:
                return None
            username = certificate.account.user.username if certificate.account and certificate.account.user else certificate.common_name
            return f"{username} / {certificate.common_name}"
        return None

    def _find_account_by_common_name(self, common_name: str) -> Optional[OpenVpnAccount]:
        return (
            self.db.query(OpenVpnAccount)
            .filter(OpenVpnAccount.vpn_username == common_name)
            .first()
        )

    def _server_online_session_count(self, server_id: int) -> int:
        return (
            self.db.query(OpenVpnSession)
            .filter(OpenVpnSession.server_id == server_id, OpenVpnSession.status == "online")
            .count()
        )

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

    def _issue_certificate_files(
        self,
        server: OpenVpnServer,
        common_name: str,
        expires_at: datetime,
        allow_existing: bool = True,
    ) -> dict:
        if server.certificate_backend == "ssh_easyrsa":
            return self._issue_remote_certificate_files(server, common_name, expires_at, allow_existing=allow_existing)
        if server.certificate_backend != "local_easyrsa":
            raise ConflictError("服务器未配置真实证书签发后端，请在服务器管理中配置 Easy-RSA 后再签发证书")

        self._validate_common_name(common_name)
        pki_dir = self._server_pki_dir(server)
        cert_path = pki_dir / "issued" / f"{common_name}.crt"
        key_path = pki_dir / "private" / f"{common_name}.key"
        request_path = pki_dir / "reqs" / f"{common_name}.req"

        if not (allow_existing and cert_path.exists() and key_path.exists()):
            valid_days = max(1, (expires_at - datetime.utcnow()).days)
            env = {"EASYRSA_CERT_EXPIRE": str(valid_days)}
            self._run_easyrsa(server, ["build-client-full", common_name, "nopass"], env=env)

        if not cert_path.exists() or not key_path.exists():
            raise ConflictError("Easy-RSA签发完成后未找到客户端证书或私钥")

        return {
            "serial_number": self._extract_certificate_serial(cert_path),
            "cert_path": str(cert_path),
            "key_path": str(key_path),
            "request_path": str(request_path) if request_path.exists() else None,
        }

    def _issue_wireguard_peer(self, server: OpenVpnServer, account: OpenVpnAccount) -> dict:
        private_key, public_key = self._generate_wireguard_keypair()
        client_address = account.wg_client_address or self._next_wireguard_client_address(server)
        server_public_key = self._wireguard_server_public_key(server)
        interface = server.wg_interface or "wg0"
        allowed_ip = f"{client_address}/32"
        command = (
            f"wg set {shlex.quote(interface)} peer {shlex.quote(public_key)} "
            f"allowed-ips {shlex.quote(allowed_ip)}"
        )
        self._run_remote_shell(server, command)
        self._run_remote_shell(server, f"wg-quick save {shlex.quote(interface)} || true")

        account.wg_client_private_key = private_key
        account.wg_client_public_key = public_key
        account.wg_client_address = client_address
        server.wg_public_key = server_public_key
        self.db.add(server)
        self.db.add(account)
        return {
            "serial_number": f"wg-{uuid4().hex}",
            "cert_path": None,
            "key_path": None,
            "request_path": None,
        }

    def _revoke_wireguard_peer(self, server: OpenVpnServer, account: OpenVpnAccount) -> None:
        if not account.wg_client_public_key:
            return
        interface = server.wg_interface or "wg0"
        command = f"wg set {shlex.quote(interface)} peer {shlex.quote(account.wg_client_public_key)} remove"
        self._run_remote_shell(server, command)
        self._run_remote_shell(server, f"wg-quick save {shlex.quote(interface)} || true")

    def _wireguard_server_public_key(self, server: OpenVpnServer) -> str:
        if server.wg_public_key:
            return server.wg_public_key
        interface = server.wg_interface or "wg0"
        public_key = self._run_remote_shell(server, f"wg show {shlex.quote(interface)} public-key", capture=True).strip()
        if not public_key:
            raise ConflictError(f"无法获取WireGuard服务器公钥，请确认接口 {interface} 已启动")
        server.wg_public_key = public_key
        self.db.add(server)
        return public_key

    def _next_wireguard_client_address(self, server: OpenVpnServer) -> str:
        network = ipaddress.ip_network(server.wg_network_cidr or "10.66.0.0/24", strict=False)
        used = {
            row[0]
            for row in self.db.query(OpenVpnAccount.wg_client_address)
            .filter(OpenVpnAccount.server_id == server.id, OpenVpnAccount.wg_client_address.isnot(None))
            .all()
        }
        hosts = list(network.hosts())
        for host in hosts[1:]:
            address = str(host)
            if address not in used:
                return address
        raise ConflictError("WireGuard客户端网段可用地址已用完")

    @staticmethod
    def _generate_wireguard_keypair() -> tuple[str, str]:
        private = x25519.X25519PrivateKey.generate()
        private_bytes = private.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(private_bytes).decode("ascii"), base64.b64encode(public_bytes).decode("ascii")

    def _revoke_certificate_files(self, server: OpenVpnServer, common_name: str) -> None:
        if server.certificate_backend == "ssh_easyrsa":
            self._validate_common_name(common_name)
            self._run_remote_easyrsa(server, ["revoke", common_name])
            self._run_remote_easyrsa(server, ["gen-crl"])
            return
        if server.certificate_backend != "local_easyrsa":
            raise ConflictError("服务器未配置真实证书签发后端，无法吊销证书")
        self._validate_common_name(common_name)
        self._run_easyrsa(server, ["revoke", common_name])
        self._run_easyrsa(server, ["gen-crl"])

    def _renew_certificate_files(self, server: OpenVpnServer, common_name: str, expires_at: datetime) -> dict:
        if server.certificate_backend == "ssh_easyrsa":
            self._validate_common_name(common_name)
            valid_days = max(1, (expires_at - datetime.utcnow()).days)
            self._run_remote_easyrsa(server, ["renew", common_name, "nopass"], env={"EASYRSA_CERT_EXPIRE": str(valid_days)})
            return self._remote_certificate_info(server, common_name)
        if server.certificate_backend != "local_easyrsa":
            raise ConflictError("服务器未配置真实证书签发后端，请在服务器管理中配置 Easy-RSA 后再续期证书")
        self._validate_common_name(common_name)
        valid_days = max(1, (expires_at - datetime.utcnow()).days)
        self._run_easyrsa(server, ["renew", common_name, "nopass"], env={"EASYRSA_CERT_EXPIRE": str(valid_days)})
        pki_dir = self._server_pki_dir(server)
        cert_path = pki_dir / "issued" / f"{common_name}.crt"
        key_path = pki_dir / "private" / f"{common_name}.key"
        request_path = pki_dir / "reqs" / f"{common_name}.req"
        if not cert_path.exists() or not key_path.exists():
            raise ConflictError("Easy-RSA续期完成后未找到客户端证书或私钥")
        return {
            "serial_number": self._extract_certificate_serial(cert_path),
            "cert_path": str(cert_path),
            "key_path": str(key_path),
            "request_path": str(request_path) if request_path.exists() else None,
        }

    def _archive_certificate_files(self, server: OpenVpnServer, account: OpenVpnAccount, cert_info: dict) -> dict:
        if server.vpn_type == "wireguard":
            return cert_info
        if cert_info.get("remote"):
            if not server.client_config_dir:
                raise ConflictError("远程证书签发必须配置证书文件输出目录")
            return self._archive_remote_certificate_files(server, account, cert_info)

        if not server.client_config_dir:
            return cert_info

        target_dir = self._account_certificate_dir(server, account)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConflictError(f"证书归档目录创建失败：{target_dir}，请检查后端写入权限：{exc}") from exc
        archived_info = dict(cert_info)
        basename = self._account_certificate_basename(server, account)

        file_map = {
            "cert_path": f"{basename}.crt",
            "key_path": f"{basename}.key",
            "request_path": f"{basename}.req",
        }
        for field_name, filename in file_map.items():
            source = cert_info.get(field_name)
            if not source:
                continue
            source_path = Path(source).expanduser()
            if not source_path.exists():
                continue
            target_path = target_dir / filename
            try:
                shutil.copy2(source_path, target_path)
                if field_name == "key_path":
                    target_path.chmod(0o600)
            except OSError as exc:
                raise ConflictError(f"证书文件归档失败：{target_path}，请检查后端写入权限：{exc}") from exc
            archived_info[field_name] = str(target_path)

        ca_source = Path(server.ca_cert_path).expanduser() if server.ca_cert_path else self._server_pki_dir(server) / "ca.crt"
        if ca_source.exists():
            try:
                shutil.copy2(ca_source, target_dir / "ca.crt")
            except OSError as exc:
                raise ConflictError(f"CA证书归档失败：{exc}") from exc
        if server.tls_crypt_key_path:
            tls_source = Path(server.tls_crypt_key_path).expanduser()
            if tls_source.exists():
                try:
                    shutil.copy2(tls_source, target_dir / "tls.key")
                except OSError as exc:
                    raise ConflictError(f"TLS密钥归档失败：{exc}") from exc

        return archived_info

    def _archive_remote_certificate_files(self, server: OpenVpnServer, account: OpenVpnAccount, cert_info: dict) -> dict:
        target_dir = self._account_certificate_dir(server, account)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConflictError(f"证书归档目录创建失败：{target_dir}，请检查后端写入权限：{exc}") from exc
        archived_info = dict(cert_info)
        basename = self._account_certificate_basename(server, account)
        file_map = {
            "cert_path": (cert_info.get("remote_cert_path"), f"{basename}.crt"),
            "key_path": (cert_info.get("remote_key_path"), f"{basename}.key"),
            "request_path": (cert_info.get("remote_request_path"), f"{basename}.req"),
        }
        for field_name, (remote_path, filename) in file_map.items():
            if not remote_path:
                continue
            target_path = target_dir / filename
            self._scp_from_remote(server, remote_path, target_path)
            if field_name == "key_path":
                target_path.chmod(0o600)
            archived_info[field_name] = str(target_path)

        ca_target = target_dir / "ca.crt"
        remote_ca_path = server.ca_cert_path or f"{self._remote_pki_dir(server)}/ca.crt"
        self._scp_from_remote(server, remote_ca_path, ca_target)
        if server.tls_crypt_key_path:
            self._scp_from_remote(server, server.tls_crypt_key_path, target_dir / "tls.key")

        return archived_info

    def _account_certificate_dir(self, server: OpenVpnServer, account: OpenVpnAccount) -> Path:
        if not server.client_config_dir:
            raise ConflictError("服务器未配置证书文件输出目录")
        server_segment = self._safe_path_segment(server.code or server.host)
        department_segment = self._account_department_segment(account)
        user_segment = self._safe_path_segment(account.user.username if account.user else account.vpn_username)
        return Path(server.client_config_dir).expanduser() / server_segment / department_segment / user_segment

    def _account_department_segment(self, account: OpenVpnAccount) -> str:
        department = (
            self.db.query(Department)
            .join(UserDepartment, UserDepartment.department_id == Department.id)
            .filter(UserDepartment.user_id == account.user_id, Department.is_deleted.is_(False))
            .order_by(UserDepartment.is_primary.desc(), Department.id.asc())
            .first()
        )
        return self._safe_path_segment(department.code if department else "未分配部门")

    def _account_certificate_basename(self, server: OpenVpnServer, account: OpenVpnAccount) -> str:
        department_code = self._account_department_segment(account)
        username = self._safe_path_segment(account.user.username if account.user else account.vpn_username)
        server_host = self._safe_path_segment(server.host)
        return f"{department_code}-{username}-{server_host}"

    @staticmethod
    def _client_config_extension(server: OpenVpnServer) -> str:
        return "conf" if server.vpn_type == "wireguard" else "ovpn"

    def _delete_account_certificate_files(self, account: OpenVpnAccount) -> None:
        certificates = (
            self.db.query(OpenVpnCertificate)
            .filter(OpenVpnCertificate.account_id == account.id)
            .all()
        )
        account_dirs: set[Path] = set()
        allowed_roots: set[Path] = set()

        related_servers = [certificate.server for certificate in certificates if certificate.server and certificate.server.client_config_dir]
        if account.server and account.server.client_config_dir:
            related_servers.append(account.server)

        for server in related_servers:
            root = Path(server.client_config_dir).expanduser()
            allowed_roots.add(root)
            try:
                account_dirs.add(self._account_certificate_dir(server, account))
            except ConflictError:
                continue

        try:
            for certificate in certificates:
                for field_name in ("cert_path", "key_path", "request_path", "config_file_path"):
                    value = getattr(certificate, field_name, None)
                    if not value:
                        continue
                    path = Path(value).expanduser()
                    if not self._is_path_under_any(path, allowed_roots):
                        continue
                    if path.exists() and (path.is_file() or path.is_symlink()):
                        path.unlink()
                    account_dirs.add(path.parent)
                    setattr(certificate, field_name, None)
                self.db.add(certificate)

            for directory in sorted(account_dirs, key=lambda item: len(item.parts), reverse=True):
                if not self._is_path_under_any(directory, allowed_roots):
                    continue
                if directory.exists():
                    shutil.rmtree(directory)
        except OSError as exc:
            raise ConflictError(f"OpenVPN账号吊销失败，证书文件删除失败：{exc}") from exc

    @staticmethod
    def _is_path_under_any(path: Path, roots: set[Path]) -> bool:
        if not roots:
            return False
        try:
            resolved_path = path.resolve()
        except OSError:
            resolved_path = path.absolute()
        for root in roots:
            try:
                resolved_path.relative_to(root.resolve())
                return True
            except (OSError, ValueError):
                continue
        return False

    @staticmethod
    def _safe_path_segment(value: str) -> str:
        value = (value or "").strip() or "未命名"
        return re.sub(r'[\\/:*?"<>|\s]+', "_", value).strip("._") or "未命名"

    def _issue_remote_certificate_files(
        self,
        server: OpenVpnServer,
        common_name: str,
        expires_at: datetime,
        allow_existing: bool = True,
    ) -> dict:
        self._validate_common_name(common_name)
        info = self._remote_certificate_info(server, common_name, check_exists=False)
        if not allow_existing or not self._remote_file_exists(server, info["remote_cert_path"], info["remote_key_path"]):
            valid_days = max(1, (expires_at - datetime.utcnow()).days)
            self._run_remote_easyrsa(server, ["build-client-full", common_name, "nopass"], env={"EASYRSA_CERT_EXPIRE": str(valid_days)})
        return self._remote_certificate_info(server, common_name)

    def _remote_certificate_info(self, server: OpenVpnServer, common_name: str, check_exists: bool = True) -> dict:
        pki_dir = self._remote_pki_dir(server)
        cert_path = f"{pki_dir}/issued/{common_name}.crt"
        key_path = f"{pki_dir}/private/{common_name}.key"
        request_path = f"{pki_dir}/reqs/{common_name}.req"
        if check_exists and not self._remote_file_exists(server, cert_path, key_path):
            raise ConflictError("远程Easy-RSA签发完成后未找到客户端证书或私钥")
        serial_number = self._remote_certificate_serial(server, cert_path) if check_exists else uuid4().hex
        return {
            "remote": True,
            "serial_number": serial_number,
            "remote_cert_path": cert_path,
            "remote_key_path": key_path,
            "remote_request_path": request_path if self._remote_file_exists(server, request_path) else None,
        }

    def _run_remote_easyrsa(self, server: OpenVpnServer, args: list[str], env: Optional[dict] = None) -> None:
        easy_rsa_dir = self._remote_easy_rsa_dir(server)
        env_prefix = ""
        if env:
            env_prefix = " ".join(f"{shlex.quote(key)}={shlex.quote(str(value))}" for key, value in env.items()) + " "
        quoted_args = " ".join(shlex.quote(arg) for arg in args)
        command = f"cd {shlex.quote(easy_rsa_dir)} && {env_prefix}./easyrsa --batch {quoted_args}"
        self._run_remote_shell(server, command)

    def _remote_certificate_serial(self, server: OpenVpnServer, cert_path: str) -> str:
        command = f"openssl x509 -in {shlex.quote(cert_path)} -noout -serial"
        result = self._run_remote_shell(server, command, capture=True)
        if "serial=" in result:
            return result.strip().split("serial=", 1)[1]
        return uuid4().hex

    def _remote_file_exists(self, server: OpenVpnServer, *paths: str) -> bool:
        checks = " && ".join(f"test -f {shlex.quote(path)}" for path in paths if path)
        if not checks:
            return False
        try:
            self._run_remote_shell(server, checks)
            return True
        except ConflictError:
            return False

    def _remote_test_command(self, server: OpenVpnServer) -> str:
        easy_rsa_dir = self._remote_easy_rsa_dir(server)
        pki_dir = self._remote_pki_dir(server)
        ca_path = server.ca_cert_path or f"{pki_dir}/ca.crt"
        tls_key_path = server.tls_crypt_key_path or settings.openvpn_default_tls_crypt_key_path
        checks = [
            ("-x", f"{easy_rsa_dir}/easyrsa", "Easy-RSA执行文件不存在或不可执行"),
            ("-d", pki_dir, "PKI目录不存在"),
            ("-f", ca_path, "CA证书不存在"),
        ]
        if tls_key_path:
            checks.append(("-f", tls_key_path, "TLS密钥不存在"))
        commands = [
            f"test {flag} {shlex.quote(path)} || {{ echo {shlex.quote(f'{message}：{path}')} >&2; exit 20; }}"
            for flag, path, message in checks
        ]
        return " && ".join(commands)

    def _run_remote_shell(self, server: OpenVpnServer, command: str, capture: bool = False) -> str:
        ssh_command = [*self._ssh_base_command(server), self._ssh_target(server), command]
        try:
            result = subprocess.run(
                ssh_command,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ConflictError("后端运行环境缺少 ssh 命令，请在生产容器/服务器中安装 openssh-client") from exc
        except subprocess.TimeoutExpired as exc:
            raise ConflictError("远程SSH命令执行超时，请检查OpenVPN服务器网络连通性或Easy-RSA执行时间") from exc
        except OSError as exc:
            raise ConflictError(f"远程SSH命令执行失败：{exc}") from exc
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "远程SSH命令执行失败").strip()
            raise ConflictError(message[-500:])
        return result.stdout.strip() if capture else ""

    def _scp_from_remote(self, server: OpenVpnServer, remote_path: str, target_path: Path) -> None:
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConflictError(f"证书归档目录创建失败：{target_path.parent}，请检查后端写入权限：{exc}") from exc
        scp_command = ["scp", "-P", str(server.ssh_port or 22), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10"]
        key_path_value = self._effective_ssh_key_path(server)
        if key_path_value:
            scp_command.extend(["-i", str(Path(key_path_value).expanduser())])
        scp_command.extend([f"{self._ssh_target(server)}:{remote_path}", str(target_path)])
        try:
            result = subprocess.run(
                scp_command,
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ConflictError("后端运行环境缺少 scp 命令，请在生产容器/服务器中安装 openssh-client") from exc
        except subprocess.TimeoutExpired as exc:
            raise ConflictError("远程证书文件拉取超时，请检查OpenVPN服务器网络连通性") from exc
        except OSError as exc:
            raise ConflictError(f"远程证书文件拉取失败：{exc}") from exc
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "远程证书文件拉取失败").strip()
            raise ConflictError(message[-500:])

    def _ssh_base_command(self, server: OpenVpnServer) -> list[str]:
        command = ["ssh", "-p", str(server.ssh_port or 22), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10"]
        key_path_value = self._effective_ssh_key_path(server)
        if key_path_value:
            key_path = Path(key_path_value).expanduser()
            if not key_path.exists():
                raise ConflictError(
                    f"SSH私钥文件不存在：{key_path}。这是后端容器内路径，生产宿主机通常对应 "
                    f"./data/oim/ssh/{server.code}.key；也可以在VPN服务器管理中编辑该服务器，填写SSH私钥内容后保存，"
                    "系统会自动写入该路径"
                )
            if not key_path.is_file():
                raise ConflictError(f"SSH私钥路径不是文件：{key_path}")
            command.extend(["-i", str(key_path)])
        return command

    def _effective_ssh_key_path(self, server: OpenVpnServer) -> Optional[str]:
        if not server.ssh_key_path:
            return self._default_server_ssh_key_path(server.code)
        key_path = Path(server.ssh_key_path).expanduser()
        if key_path.exists():
            return str(key_path)
        code_key_path_value = self._default_server_ssh_key_path(server.code)
        code_key_path = Path(code_key_path_value).expanduser() if code_key_path_value else None
        if code_key_path and code_key_path.exists():
            return str(code_key_path)
        default_key_path = Path(settings.openvpn_default_ssh_key_path).expanduser() if settings.openvpn_default_ssh_key_path else None
        if default_key_path and default_key_path.exists():
            return str(default_key_path)
        return server.ssh_key_path

    def _ssh_target(self, server: OpenVpnServer) -> str:
        if not server.ssh_user:
            raise ConflictError("服务器未配置证书服务器SSH用户")
        host = server.ssh_host or server.host
        if not host:
            raise ConflictError("服务器未配置证书服务器SSH地址")
        return f"{server.ssh_user}@{host}"

    def _remote_easy_rsa_dir(self, server: OpenVpnServer) -> str:
        if not server.easy_rsa_dir:
            raise ConflictError("服务器未配置远程Easy-RSA目录")
        return server.easy_rsa_dir.rstrip("/")

    def _remote_pki_dir(self, server: OpenVpnServer) -> str:
        if server.pki_dir:
            return server.pki_dir.rstrip("/")
        return f"{self._remote_easy_rsa_dir(server)}/pki"

    def _run_easyrsa(self, server: OpenVpnServer, args: list[str], env: Optional[dict] = None) -> None:
        if not server.easy_rsa_dir:
            raise ConflictError("服务器未配置Easy-RSA目录")
        easy_rsa_dir = Path(server.easy_rsa_dir).expanduser()
        executable = easy_rsa_dir / "easyrsa"
        if not executable.exists():
            raise ConflictError(f"Easy-RSA执行文件不存在：{executable}")
        process_env = None
        if env:
            import os

            process_env = {**os.environ, **env}
        try:
            result = subprocess.run(
                [str(executable), "--batch", *args],
                cwd=str(easy_rsa_dir),
                env=process_env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConflictError("Easy-RSA执行超时，请检查服务器负载或证书后端配置") from exc
        except OSError as exc:
            raise ConflictError(f"Easy-RSA执行失败：{exc}") from exc
        if result.returncode != 0:
            message = (result.stderr or result.stdout or "Easy-RSA执行失败").strip()
            raise ConflictError(message[-500:])

    def _server_pki_dir(self, server: OpenVpnServer) -> Path:
        if server.pki_dir:
            return Path(server.pki_dir).expanduser()
        if not server.easy_rsa_dir:
            raise ConflictError("服务器未配置PKI目录或Easy-RSA目录")
        return Path(server.easy_rsa_dir).expanduser() / "pki"

    def _render_client_config(self, server: OpenVpnServer, certificate: OpenVpnCertificate) -> str:
        if server.vpn_type == "wireguard":
            account = self.get_account_required(certificate.account_id)
            return self._render_wireguard_client_config(server, account)
        if server.certificate_backend not in ("local_easyrsa", "ssh_easyrsa"):
            raise ConflictError("服务器未配置真实证书签发后端，无法生成可用的OpenVPN配置")
        template = server.config_template or self._default_config_template()
        values = {
            "host": server.host,
            "port": server.port,
            "protocol": server.protocol,
            "common_name": certificate.common_name,
            "serial_number": certificate.serial_number,
            "ca": "",
            "cert": "",
            "key": "",
            "tls_crypt": "",
            "tls_crypt_block": "",
        }
        if not certificate.cert_path or not certificate.key_path:
            raise ConflictError("证书记录缺少客户端证书或私钥路径")
        cert_path = Path(certificate.cert_path).expanduser()
        key_path = Path(certificate.key_path).expanduser()
        if server.certificate_backend == "ssh_easyrsa":
            ca_path = cert_path.parent / "ca.crt"
            tls_crypt_path = cert_path.parent / "tls.key"
        else:
            ca_path = Path(server.ca_cert_path).expanduser() if server.ca_cert_path else self._server_pki_dir(server) / "ca.crt"
            tls_crypt_path = Path(server.tls_crypt_key_path).expanduser() if server.tls_crypt_key_path else None
        values.update(
            {
                "ca": self._read_file(ca_path),
                "cert": self._read_file(cert_path),
                "key": self._read_file(key_path),
                "tls_crypt": self._read_file(tls_crypt_path) if tls_crypt_path and tls_crypt_path.exists() else "",
            }
        )
        if values["tls_crypt"]:
            values["tls_crypt_block"] = f"<tls-crypt>\n{values['tls_crypt']}\n</tls-crypt>"
        return template.format(**values)

    def _render_wireguard_client_config(self, server: OpenVpnServer, account: OpenVpnAccount) -> str:
        if not account.wg_client_private_key or not account.wg_client_address:
            raise ConflictError("WireGuard客户端凭据不完整，请重新签发")
        server_public_key = self._wireguard_server_public_key(server)
        dns = server.wg_dns or "1.1.1.1,1.0.0.1"
        allowed_ips = server.wg_allowed_ips or "0.0.0.0/0,::/0"
        keepalive = server.wg_persistent_keepalive if server.wg_persistent_keepalive is not None else 25
        lines = [
            "[Interface]",
            f"PrivateKey = {account.wg_client_private_key}",
            f"Address = {account.wg_client_address}/32",
            f"DNS = {dns}",
            "",
            "[Peer]",
            f"PublicKey = {server_public_key}",
            f"Endpoint = {server.host}:{server.port}",
            f"AllowedIPs = {allowed_ips}",
        ]
        if keepalive:
            lines.append(f"PersistentKeepalive = {keepalive}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _validate_common_name(common_name: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,128}", common_name or ""):
            raise ConflictError("VPN用户名只能包含字母、数字、点、下划线、@和短横线")

    @staticmethod
    def _read_file(path: Path) -> str:
        if not path.exists():
            raise ConflictError(f"文件不存在：{path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _extract_certificate_serial(cert_path: Path) -> str:
        result = subprocess.run(
            ["openssl", "x509", "-in", str(cert_path), "-noout", "-serial"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode == 0 and "serial=" in result.stdout:
            return result.stdout.strip().split("serial=", 1)[1]
        return uuid4().hex

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
dhcp-option DNS 1.1.1.1
dhcp-option DNS 1.0.0.1
verb 3

<ca>
{ca}
</ca>
<cert>
{cert}
</cert>
<key>
{key}
</key>
{tls_crypt_block}
"""
