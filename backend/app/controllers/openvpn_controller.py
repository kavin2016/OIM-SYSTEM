from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from ..dependencies import OpenVpnServiceDep, OperationLogServiceDep
from ..config import settings
from ..models.openvpn import (
    OpenVpnAccount,
    OpenVpnCertificate,
    OpenVpnConnectionLog,
    OpenVpnServer,
    OpenVpnSession,
    OpenVpnTrafficAlert,
    OpenVpnTrafficThresholdRule,
)
from ..schemas.openvpn import (
    OpenVpnAccountRead,
    OpenVpnAssignServer,
    OpenVpnAssignmentRuleCreate,
    OpenVpnAssignmentRuleRead,
    OpenVpnAssignmentRuleUpdate,
    OpenVpnCertificateRead,
    OpenVpnConfigRead,
    OpenVpnConnectionLogRead,
    OpenVpnEnableAccount,
    OpenVpnIssueCertificate,
    OpenVpnResolvedServer,
    OpenVpnRevokeCertificate,
    OpenVpnSessionEvent,
    OpenVpnServerCreate,
    OpenVpnServerRead,
    OpenVpnServerUpdate,
    OpenVpnSessionRead,
    OpenVpnTrafficAlertProcess,
    OpenVpnTrafficAlertRead,
    OpenVpnTrafficMetric,
    OpenVpnTrafficOverview,
    OpenVpnTrafficThresholdRuleCreate,
    OpenVpnTrafficThresholdRuleRead,
    OpenVpnTrafficThresholdRuleUpdate,
    OpenVpnTrafficTrendItem,
)
from ..security import require_permission
from ..services.data_scope import ensure_user_in_scope, scoped_department_ids, scoped_user_ids

router = APIRouter(prefix="/openvpn", tags=["openvpn"])


def verify_openvpn_event_token(x_openvpn_token: Optional[str] = Header(default=None)):
    if not settings.openvpn_event_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OpenVPN事件回调密钥未配置")
    if x_openvpn_token != settings.openvpn_event_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OpenVPN事件回调密钥无效")


def _account_read(account: OpenVpnAccount) -> OpenVpnAccountRead:
    latest_cert = None
    if account.certificates:
        latest_cert = sorted(account.certificates, key=lambda item: item.expires_at, reverse=True)[0]
    return OpenVpnAccountRead(
        **{field: getattr(account, field) for field in OpenVpnAccountRead.model_fields if hasattr(account, field)},
        username=account.user.username if account.user else None,
        nickname=account.user.nickname if account.user else None,
        server_name=account.server.name if account.server else None,
        server_vpn_type=account.server.vpn_type if account.server else None,
        certificate_id=latest_cert.id if latest_cert else None,
        certificate_status=latest_cert.status if latest_cert else None,
        certificate_serial_number=latest_cert.serial_number if latest_cert else None,
        certificate_expires_at=latest_cert.expires_at if latest_cert else None,
    )


def _certificate_read(certificate: OpenVpnCertificate) -> OpenVpnCertificateRead:
    return OpenVpnCertificateRead(
        **{field: getattr(certificate, field) for field in OpenVpnCertificateRead.model_fields if hasattr(certificate, field)},
        username=certificate.account.user.username if certificate.account and certificate.account.user else None,
        server_name=certificate.server.name if certificate.server else None,
    )


def _session_read(session: OpenVpnSession, service) -> OpenVpnSessionRead:
    account = service.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == session.account_id).first() if session.account_id else None
    server = service.db.query(OpenVpnServer).filter(OpenVpnServer.id == session.server_id).first() if session.server_id else None
    return OpenVpnSessionRead(
        **{field: getattr(session, field) for field in OpenVpnSessionRead.model_fields if hasattr(session, field)},
        username=account.user.username if account and account.user else None,
        server_name=server.name if server else None,
    )


def _log_read(log: OpenVpnConnectionLog, service) -> OpenVpnConnectionLogRead:
    account = service.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == log.account_id).first() if log.account_id else None
    return OpenVpnConnectionLogRead(
        **{field: getattr(log, field) for field in OpenVpnConnectionLogRead.model_fields if hasattr(log, field)},
        username=account.user.username if account and account.user else None,
        server_name=account.server.name if account and account.server else None,
    )


def _traffic_rule_read(rule: OpenVpnTrafficThresholdRule, service) -> OpenVpnTrafficThresholdRuleRead:
    return OpenVpnTrafficThresholdRuleRead(
        **{field: getattr(rule, field) for field in OpenVpnTrafficThresholdRuleRead.model_fields if hasattr(rule, field)},
        target_name=service.traffic_target_name(rule.target_type, rule.target_id),
    )


def _ensure_traffic_threshold_target_in_scope(service, current_user, target_type: Optional[str], target_id: Optional[int]) -> None:
    if target_type != "certificate" or not target_id:
        return
    certificate = service.get_certificate_required(target_id)
    account = service.get_account_required(certificate.account_id)
    ensure_user_in_scope(service.db, current_user, account.user_id, detail="无权管理该用户VPN证书的流量阈值")


def _traffic_alert_read(alert: OpenVpnTrafficAlert, service) -> OpenVpnTrafficAlertRead:
    server = service.db.query(OpenVpnServer).filter(OpenVpnServer.id == alert.server_id).first() if alert.server_id else None
    account = service.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == alert.account_id).first() if alert.account_id else None
    return OpenVpnTrafficAlertRead(
        **{field: getattr(alert, field) for field in OpenVpnTrafficAlertRead.model_fields if hasattr(alert, field)},
        target_name=service.traffic_target_name(alert.target_type, alert.target_id),
        server_name=server.name if server else None,
        username=account.user.username if account and account.user else None,
    )


@router.get("/servers", response_model=list[OpenVpnServerRead])
def list_servers(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    include_disabled: bool = False,
    include_deleted: bool = False,
    name: Optional[str] = None,
    code: Optional[str] = None,
    status: Optional[str] = None,
    region: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:server:query")),
):
    return openvpn_service.list_servers(skip, limit, include_disabled, include_deleted, name, code, status, region)


@router.get("/options")
def list_openvpn_options(
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:query")),
):
    return openvpn_service.list_options(scoped_user_ids(openvpn_service.db, current_user))


@router.post("/servers", response_model=OpenVpnServerRead, status_code=status.HTTP_201_CREATED)
def create_server(
    request: Request,
    payload: OpenVpnServerCreate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:create")),
):
    item = openvpn_service.create_server(payload, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_server",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增OpenVPN服务器",
        request=request,
        request_body=payload,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.get("/servers/{server_id}", response_model=OpenVpnServerRead)
def get_server(
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:query")),
):
    return openvpn_service.get_server_required(server_id, include_deleted=True)


@router.put("/servers/{server_id}", response_model=OpenVpnServerRead)
def update_server(
    request: Request,
    server_id: int,
    payload: OpenVpnServerUpdate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:update")),
):
    item = openvpn_service.update_server(server_id, payload, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_server",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改OpenVPN服务器",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.delete("/servers/{server_id}", response_model=OpenVpnServerRead)
def delete_server(
    request: Request,
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:delete")),
):
    item = openvpn_service.delete_server(server_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_server",
        resource_id=item.id,
        resource_name=item.name,
        action="delete",
        action_name="删除OpenVPN服务器",
        request=request,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.post("/servers/{server_id}/set-default", response_model=OpenVpnServerRead)
def set_default_server(
    request: Request,
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:set-default")),
):
    item = openvpn_service.set_default_server(server_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_server",
        resource_id=item.id,
        resource_name=item.name,
        action="set-default",
        action_name="设置默认OpenVPN服务器",
        request=request,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.post("/servers/{server_id}/test")
def test_server(
    request: Request,
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:test")),
):
    result = openvpn_service.test_server(server_id)
    server = openvpn_service.get_server_required(server_id, include_deleted=True)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_server",
        resource_id=server.id,
        resource_name=server.name,
        action="test",
        action_name="测试OpenVPN服务器",
        request=request,
        response_params=result,
    )
    return result


@router.get("/assignment-rules", response_model=list[OpenVpnAssignmentRuleRead])
def list_rules(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    server_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user=Depends(require_permission("ops:openvpn:rule:query")),
):
    return openvpn_service.list_rules(skip, limit, server_id, target_type, target_id, is_active)


@router.post("/assignment-rules", response_model=OpenVpnAssignmentRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    request: Request,
    payload: OpenVpnAssignmentRuleCreate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:rule:create")),
):
    item = openvpn_service.create_rule(payload, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_rule",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增OpenVPN分配策略",
        request=request,
        request_body=payload,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.put("/assignment-rules/{rule_id}", response_model=OpenVpnAssignmentRuleRead)
def update_rule(
    request: Request,
    rule_id: int,
    payload: OpenVpnAssignmentRuleUpdate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:rule:update")),
):
    item = openvpn_service.update_rule(rule_id, payload, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_rule",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改OpenVPN分配策略",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.delete("/assignment-rules/{rule_id}", response_model=OpenVpnAssignmentRuleRead)
def delete_rule(
    request: Request,
    rule_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:rule:delete")),
):
    rule = openvpn_service.get_rule_required(rule_id)
    payload = OpenVpnAssignmentRuleRead.model_validate(rule)
    openvpn_service.delete_rule(rule_id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_rule",
        resource_id=payload.id,
        resource_name=payload.name,
        action="delete",
        action_name="删除OpenVPN分配策略",
        request=request,
        response_params={"id": payload.id, "name": payload.name},
    )
    return payload


@router.get("/accounts", response_model=list[OpenVpnAccountRead])
def list_accounts(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    username: Optional[str] = None,
    status: Optional[str] = None,
    server_id: Optional[int] = None,
    department_id: Optional[int] = None,
    user_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:account:query")),
):
    scope_ids = scoped_user_ids(openvpn_service.db, current_user, user_id=user_id, department_id=department_id)
    return [_account_read(item) for item in openvpn_service.list_accounts(skip, limit, username, status, server_id, department_id, scope_user_ids=scope_ids)]


@router.post("/accounts/{user_id}/enable", response_model=OpenVpnAccountRead)
def enable_account(
    request: Request,
    user_id: int,
    payload: OpenVpnEnableAccount,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:enable")),
):
    ensure_user_in_scope(openvpn_service.db, current_user, user_id, detail="无权开通该用户VPN账号")
    item = _account_read(openvpn_service.enable_account(user_id, payload, actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_account",
        resource_id=item.id,
        resource_name=item.vpn_username,
        action="enable",
        action_name="启用OpenVPN账号",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "vpn_username": item.vpn_username, "user_id": item.user_id},
    )
    return item


@router.post("/accounts/{user_id}/disable", response_model=OpenVpnAccountRead)
def disable_account(
    request: Request,
    user_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:disable")),
):
    ensure_user_in_scope(openvpn_service.db, current_user, user_id, detail="无权禁用该用户VPN账号")
    item = _account_read(openvpn_service.disable_account(user_id, actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_account",
        resource_id=item.id,
        resource_name=item.vpn_username,
        action="disable",
        action_name="禁用OpenVPN账号",
        request=request,
        response_params={"id": item.id, "vpn_username": item.vpn_username, "user_id": item.user_id},
    )
    return item


@router.post("/accounts/{account_id}/revoke", response_model=OpenVpnAccountRead)
def revoke_account(
    request: Request,
    account_id: int,
    payload: OpenVpnRevokeCertificate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:revoke")),
):
    account = openvpn_service.get_account_required(account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id, detail="无权吊销该用户VPN账号")
    item = _account_read(openvpn_service.revoke_account(account_id, payload.reason, actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_account",
        resource_id=item.id,
        resource_name=item.vpn_username,
        action="revoke",
        action_name="吊销OpenVPN账号",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "vpn_username": item.vpn_username, "status": item.status},
    )
    return item


@router.post("/accounts/{account_id}/assign-server", response_model=OpenVpnAccountRead)
def assign_account_server(
    request: Request,
    account_id: int,
    payload: OpenVpnAssignServer,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:assign-server")),
):
    account = openvpn_service.get_account_required(account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id, detail="无权分配该用户VPN服务器")
    item = _account_read(openvpn_service.assign_account_server(account_id, payload.server_id, actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_account",
        resource_id=item.id,
        resource_name=item.vpn_username,
        action="assign-server",
        action_name="分配OpenVPN服务器",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "vpn_username": item.vpn_username, "server_id": item.server_id},
    )
    return item


@router.get("/accounts/{account_id}/resolved-server", response_model=OpenVpnResolvedServer)
def get_resolved_server(
    account_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:query")),
):
    account = openvpn_service.get_account_required(account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id)
    server, source, rule_id = openvpn_service.resolve_user_server(account.user_id)
    return {"server": server, "assign_source": source, "assignment_rule_id": rule_id}


@router.get("/accounts/{account_id}/download-config", response_model=OpenVpnConfigRead)
def download_config(
    request: Request,
    account_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:download-config")),
):
    account = openvpn_service.get_account_required(account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id, detail="无权下载该用户VPN配置")
    filename, content = openvpn_service.generate_config(account_id, actor_id=current_user.id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_account",
        resource_id=account.id,
        resource_name=account.vpn_username,
        action="download-config",
        action_name="下载OpenVPN配置",
        request=request,
        response_params={"filename": filename, "account_id": account.id},
    )
    return {"filename": filename, "content": content}


@router.get("/certificates", response_model=list[OpenVpnCertificateRead])
def list_certificates(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None,
    server_id: Optional[int] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:cert:query")),
):
    scope_ids = scoped_user_ids(openvpn_service.db, current_user, user_id=user_id, department_id=department_id)
    return [_certificate_read(item) for item in openvpn_service.list_certificates(skip, limit, account_id, server_id, status, scope_user_ids=scope_ids)]


@router.post("/accounts/{account_id}/certificates/issue", response_model=OpenVpnCertificateRead)
def issue_certificate(
    request: Request,
    account_id: int,
    payload: OpenVpnIssueCertificate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:cert:issue")),
):
    account = openvpn_service.get_account_required(account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id, detail="无权为该用户签发VPN证书")
    item = _certificate_read(openvpn_service.issue_certificate(account_id, payload.resolved_expires_at(), actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_certificate",
        resource_id=item.id,
        resource_name=item.common_name,
        action="issue",
        action_name="签发OpenVPN证书",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "common_name": item.common_name, "account_id": item.account_id},
    )
    return item


@router.post("/certificates/{certificate_id}/revoke", response_model=OpenVpnCertificateRead)
def revoke_certificate(
    request: Request,
    certificate_id: int,
    payload: OpenVpnRevokeCertificate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:cert:revoke")),
):
    certificate = openvpn_service.get_certificate_required(certificate_id)
    account = openvpn_service.get_account_required(certificate.account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id, detail="无权吊销该用户VPN证书")
    item = _certificate_read(openvpn_service.revoke_certificate(certificate_id, payload.reason, actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_certificate",
        resource_id=item.id,
        resource_name=item.common_name,
        action="revoke",
        action_name="吊销OpenVPN证书",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "common_name": item.common_name, "status": item.status},
    )
    return item


@router.post("/certificates/{certificate_id}/renew", response_model=OpenVpnCertificateRead)
def renew_certificate(
    request: Request,
    certificate_id: int,
    payload: OpenVpnIssueCertificate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:cert:renew")),
):
    certificate = openvpn_service.get_certificate_required(certificate_id)
    account = openvpn_service.get_account_required(certificate.account_id)
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id, detail="无权续期该用户VPN证书")
    item = _certificate_read(openvpn_service.renew_certificate(certificate_id, payload.resolved_expires_at(), actor_id=current_user.id))
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_certificate",
        resource_id=item.id,
        resource_name=item.common_name,
        action="renew",
        action_name="续期OpenVPN证书",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "common_name": item.common_name, "expires_at": item.expires_at},
    )
    return item


@router.get("/traffic/overview", response_model=OpenVpnTrafficOverview)
def get_traffic_overview(
    openvpn_service: OpenVpnServiceDep,
    period_type: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:traffic:query")),
):
    scope_department_ids = scoped_department_ids(openvpn_service.db, current_user, department_id=department_id)
    return openvpn_service.traffic_overview(period_type, date_from, date_to, scope_department_ids)


@router.get("/traffic/distribution", response_model=list[OpenVpnTrafficMetric])
def get_traffic_distribution(
    openvpn_service: OpenVpnServiceDep,
    dimension: str = "server",
    period_type: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:traffic:query")),
):
    scope_department_ids = scoped_department_ids(openvpn_service.db, current_user, department_id=department_id)
    return openvpn_service.traffic_distribution(dimension, period_type, date_from, date_to, scope_department_ids)


@router.get("/traffic/trend", response_model=list[OpenVpnTrafficTrendItem])
def get_traffic_trend(
    openvpn_service: OpenVpnServiceDep,
    period_type: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    dimension: Optional[str] = None,
    target_id: Optional[int] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:traffic:query")),
):
    scope_department_ids = scoped_department_ids(openvpn_service.db, current_user, department_id=department_id)
    return openvpn_service.traffic_trend(period_type, date_from, date_to, dimension, target_id, scope_department_ids)


@router.get("/traffic/ranking", response_model=list[OpenVpnTrafficMetric])
def get_traffic_ranking(
    openvpn_service: OpenVpnServiceDep,
    dimension: str = "certificate",
    period_type: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = 10,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:traffic:query")),
):
    scope_department_ids = scoped_department_ids(openvpn_service.db, current_user, department_id=department_id)
    return openvpn_service.traffic_ranking(dimension, period_type, date_from, date_to, limit, scope_department_ids)


@router.get("/traffic/threshold-rules", response_model=list[OpenVpnTrafficThresholdRuleRead])
def list_traffic_threshold_rules(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:traffic:threshold:query")),
):
    scope_department_ids = scoped_department_ids(openvpn_service.db, current_user, department_id=department_id)
    return [
        _traffic_rule_read(item, openvpn_service)
        for item in openvpn_service.list_traffic_threshold_rules(skip, limit, target_type, target_id, is_active, scope_department_ids)
    ]


@router.post("/traffic/threshold-rules", response_model=OpenVpnTrafficThresholdRuleRead, status_code=status.HTTP_201_CREATED)
def create_traffic_threshold_rule(
    request: Request,
    payload: OpenVpnTrafficThresholdRuleCreate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:traffic:threshold:create")),
):
    _ensure_traffic_threshold_target_in_scope(openvpn_service, current_user, payload.target_type, payload.target_id)
    item = _traffic_rule_read(openvpn_service.create_traffic_threshold_rule(payload, current_user.id), openvpn_service)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_traffic_threshold",
        resource_id=item.id,
        resource_name=item.name,
        action="create",
        action_name="新增OpenVPN流量阈值",
        request=request,
        request_body=payload,
        response_status=status.HTTP_201_CREATED,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.put("/traffic/threshold-rules/{rule_id}", response_model=OpenVpnTrafficThresholdRuleRead)
def update_traffic_threshold_rule(
    request: Request,
    rule_id: int,
    payload: OpenVpnTrafficThresholdRuleUpdate,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:traffic:threshold:update")),
):
    rule = openvpn_service.get_traffic_threshold_rule_required(rule_id)
    _ensure_traffic_threshold_target_in_scope(openvpn_service, current_user, rule.target_type, rule.target_id)
    update_data = payload.model_dump(exclude_unset=True)
    _ensure_traffic_threshold_target_in_scope(
        openvpn_service,
        current_user,
        update_data.get("target_type", rule.target_type),
        update_data.get("target_id", rule.target_id),
    )
    item = _traffic_rule_read(openvpn_service.update_traffic_threshold_rule(rule_id, payload, current_user.id), openvpn_service)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_traffic_threshold",
        resource_id=item.id,
        resource_name=item.name,
        action="update",
        action_name="修改OpenVPN流量阈值",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "name": item.name},
    )
    return item


@router.delete("/traffic/threshold-rules/{rule_id}", response_model=OpenVpnTrafficThresholdRuleRead)
def delete_traffic_threshold_rule(
    request: Request,
    rule_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:traffic:threshold:delete")),
):
    rule = openvpn_service.get_traffic_threshold_rule_required(rule_id)
    _ensure_traffic_threshold_target_in_scope(openvpn_service, current_user, rule.target_type, rule.target_id)
    payload = _traffic_rule_read(rule, openvpn_service)
    openvpn_service.delete_traffic_threshold_rule(rule_id)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_traffic_threshold",
        resource_id=payload.id,
        resource_name=payload.name,
        action="delete",
        action_name="删除OpenVPN流量阈值",
        request=request,
        response_params={"id": payload.id, "name": payload.name},
    )
    return payload


@router.get("/traffic/alerts", response_model=list[OpenVpnTrafficAlertRead])
def list_traffic_alerts(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    department_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:traffic:alert:query")),
):
    scope_department_ids = scoped_department_ids(openvpn_service.db, current_user, department_id=department_id)
    return [
        _traffic_alert_read(item, openvpn_service)
        for item in openvpn_service.list_traffic_alerts(skip, limit, status, target_type, target_id, scope_department_ids)
    ]


@router.post("/traffic/alerts/{alert_id}/process", response_model=OpenVpnTrafficAlertRead)
def process_traffic_alert(
    request: Request,
    alert_id: int,
    payload: OpenVpnTrafficAlertProcess,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:traffic:alert:process")),
):
    alert = openvpn_service.db.query(OpenVpnTrafficAlert).filter(OpenVpnTrafficAlert.id == alert_id).first()
    account = openvpn_service.get_account_required(alert.account_id) if alert and alert.account_id else None
    ensure_user_in_scope(openvpn_service.db, current_user, account.user_id if account else None, detail="无权处理该流量告警")
    item = _traffic_alert_read(openvpn_service.process_traffic_alert(alert_id, payload.note, current_user.id), openvpn_service)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_traffic_alert",
        resource_id=item.id,
        resource_name=item.target_name,
        action="process",
        action_name="处理OpenVPN流量告警",
        request=request,
        request_body=payload,
        response_params={"id": item.id, "status": item.status, "target_name": item.target_name},
    )
    return item


@router.post("/events/connect", response_model=OpenVpnSessionRead)
def record_openvpn_connect_event(
    payload: OpenVpnSessionEvent,
    openvpn_service: OpenVpnServiceDep,
    _=Depends(verify_openvpn_event_token),
):
    return _session_read(openvpn_service.record_session_connect(payload), openvpn_service)


@router.post("/events/disconnect", response_model=OpenVpnSessionRead)
def record_openvpn_disconnect_event(
    payload: OpenVpnSessionEvent,
    openvpn_service: OpenVpnServiceDep,
    _=Depends(verify_openvpn_event_token),
):
    return _session_read(openvpn_service.record_session_disconnect(payload), openvpn_service)


@router.get("/sessions", response_model=list[OpenVpnSessionRead])
def list_sessions(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    server_id: Optional[int] = None,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:session:query")),
):
    scope_ids = scoped_user_ids(openvpn_service.db, current_user, user_id=user_id, department_id=department_id)
    return [_session_read(item, openvpn_service) for item in openvpn_service.list_sessions(skip, limit, server_id, user_id, status, scope_user_ids=scope_ids)]


@router.post("/sessions/{session_id}/kick", response_model=OpenVpnSessionRead)
def kick_session(
    request: Request,
    session_id: int,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    current_user=Depends(require_permission("ops:openvpn:session:kick")),
):
    session = openvpn_service.db.query(OpenVpnSession).filter(OpenVpnSession.id == session_id).first()
    ensure_user_in_scope(openvpn_service.db, current_user, session.user_id if session else None, detail="无权操作该用户VPN会话")
    item = _session_read(openvpn_service.kick_session(session_id), openvpn_service)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_session",
        resource_id=item.id,
        resource_name=item.username,
        action="kick",
        action_name="强制下线OpenVPN会话",
        request=request,
        response_params={"id": item.id, "username": item.username, "server_name": item.server_name},
    )
    return item


@router.get("/logs", response_model=list[OpenVpnConnectionLogRead])
def list_logs(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    server_id: Optional[int] = None,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    cursor_id: Optional[int] = None,
    current_user=Depends(require_permission("ops:openvpn:log:query")),
):
    scope_ids = scoped_user_ids(openvpn_service.db, current_user, user_id=user_id, department_id=department_id)
    return [
        _log_read(item, openvpn_service)
        for item in openvpn_service.list_logs(skip, limit, server_id, user_id, action, result, cursor_id, scope_user_ids=scope_ids)
    ]


@router.get("/logs/export", response_model=OpenVpnConfigRead)
def export_logs(
    request: Request,
    openvpn_service: OpenVpnServiceDep,
    operation_log_service: OperationLogServiceDep,
    server_id: Optional[int] = None,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
    action: Optional[str] = None,
    result: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:log:export")),
):
    scope_ids = scoped_user_ids(openvpn_service.db, current_user, user_id=user_id, department_id=department_id)
    filename, content = openvpn_service.export_logs_csv(server_id=server_id, user_id=user_id, action=action, result=result, scope_user_ids=scope_ids)
    operation_log_service.record(
        actor=current_user,
        module="ops",
        module_name="运维管理",
        resource_type="openvpn_log",
        action="export",
        action_name="导出OpenVPN连接日志",
        request=request,
        response_params={"filename": filename, "server_id": server_id, "user_id": user_id, "action": action},
    )
    return {"filename": filename, "content": content}
