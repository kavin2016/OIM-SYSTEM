from typing import Optional

from fastapi import APIRouter, Depends, status

from ..dependencies import OpenVpnServiceDep
from ..models.openvpn import OpenVpnAccount, OpenVpnCertificate, OpenVpnConnectionLog, OpenVpnSession
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
    OpenVpnServerCreate,
    OpenVpnServerRead,
    OpenVpnServerUpdate,
    OpenVpnSessionRead,
)
from ..security import require_permission

router = APIRouter(prefix="/openvpn", tags=["openvpn"])


def _account_read(account: OpenVpnAccount) -> OpenVpnAccountRead:
    latest_cert = None
    if account.certificates:
        latest_cert = sorted(account.certificates, key=lambda item: item.expires_at, reverse=True)[0]
    return OpenVpnAccountRead(
        **{field: getattr(account, field) for field in OpenVpnAccountRead.model_fields if hasattr(account, field)},
        username=account.user.username if account.user else None,
        nickname=account.user.nickname if account.user else None,
        server_name=account.server.name if account.server else None,
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
    return OpenVpnSessionRead(
        **{field: getattr(session, field) for field in OpenVpnSessionRead.model_fields if hasattr(session, field)},
        username=account.user.username if account and account.user else None,
        server_name=account.server.name if account and account.server else None,
    )


def _log_read(log: OpenVpnConnectionLog, service) -> OpenVpnConnectionLogRead:
    account = service.db.query(OpenVpnAccount).filter(OpenVpnAccount.id == log.account_id).first() if log.account_id else None
    return OpenVpnConnectionLogRead(
        **{field: getattr(log, field) for field in OpenVpnConnectionLogRead.model_fields if hasattr(log, field)},
        username=account.user.username if account and account.user else None,
        server_name=account.server.name if account and account.server else None,
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
    return openvpn_service.list_options()


@router.post("/servers", response_model=OpenVpnServerRead, status_code=status.HTTP_201_CREATED)
def create_server(
    payload: OpenVpnServerCreate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:create")),
):
    return openvpn_service.create_server(payload, actor_id=current_user.id)


@router.get("/servers/{server_id}", response_model=OpenVpnServerRead)
def get_server(
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:query")),
):
    return openvpn_service.get_server_required(server_id, include_deleted=True)


@router.put("/servers/{server_id}", response_model=OpenVpnServerRead)
def update_server(
    server_id: int,
    payload: OpenVpnServerUpdate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:update")),
):
    return openvpn_service.update_server(server_id, payload, actor_id=current_user.id)


@router.delete("/servers/{server_id}", response_model=OpenVpnServerRead)
def delete_server(
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:delete")),
):
    return openvpn_service.delete_server(server_id, actor_id=current_user.id)


@router.post("/servers/{server_id}/set-default", response_model=OpenVpnServerRead)
def set_default_server(
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:set-default")),
):
    return openvpn_service.set_default_server(server_id, actor_id=current_user.id)


@router.post("/servers/{server_id}/test")
def test_server(
    server_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:server:test")),
):
    return openvpn_service.test_server(server_id)


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
    payload: OpenVpnAssignmentRuleCreate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:rule:create")),
):
    return openvpn_service.create_rule(payload, actor_id=current_user.id)


@router.put("/assignment-rules/{rule_id}", response_model=OpenVpnAssignmentRuleRead)
def update_rule(
    rule_id: int,
    payload: OpenVpnAssignmentRuleUpdate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:rule:update")),
):
    return openvpn_service.update_rule(rule_id, payload, actor_id=current_user.id)


@router.delete("/assignment-rules/{rule_id}", response_model=OpenVpnAssignmentRuleRead)
def delete_rule(
    rule_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:rule:delete")),
):
    rule = openvpn_service.get_rule_required(rule_id)
    payload = OpenVpnAssignmentRuleRead.model_validate(rule)
    openvpn_service.delete_rule(rule_id)
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
    current_user=Depends(require_permission("ops:openvpn:account:query")),
):
    return [_account_read(item) for item in openvpn_service.list_accounts(skip, limit, username, status, server_id, department_id)]


@router.post("/accounts/{user_id}/enable", response_model=OpenVpnAccountRead)
def enable_account(
    user_id: int,
    payload: OpenVpnEnableAccount,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:enable")),
):
    return _account_read(openvpn_service.enable_account(user_id, payload, actor_id=current_user.id))


@router.post("/accounts/{user_id}/disable", response_model=OpenVpnAccountRead)
def disable_account(
    user_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:disable")),
):
    return _account_read(openvpn_service.disable_account(user_id, actor_id=current_user.id))


@router.post("/accounts/{account_id}/assign-server", response_model=OpenVpnAccountRead)
def assign_account_server(
    account_id: int,
    payload: OpenVpnAssignServer,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:assign-server")),
):
    return _account_read(openvpn_service.assign_account_server(account_id, payload.server_id, actor_id=current_user.id))


@router.get("/accounts/{account_id}/resolved-server", response_model=OpenVpnResolvedServer)
def get_resolved_server(
    account_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:query")),
):
    account = openvpn_service.get_account_required(account_id)
    server, source, rule_id = openvpn_service.resolve_user_server(account.user_id)
    return {"server": server, "assign_source": source, "assignment_rule_id": rule_id}


@router.get("/accounts/{account_id}/download-config", response_model=OpenVpnConfigRead)
def download_config(
    account_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:account:download-config")),
):
    filename, content = openvpn_service.generate_config(account_id, actor_id=current_user.id)
    return {"filename": filename, "content": content}


@router.get("/certificates", response_model=list[OpenVpnCertificateRead])
def list_certificates(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    account_id: Optional[int] = None,
    server_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:cert:query")),
):
    return [_certificate_read(item) for item in openvpn_service.list_certificates(skip, limit, account_id, server_id, status)]


@router.post("/accounts/{account_id}/certificates/issue", response_model=OpenVpnCertificateRead)
def issue_certificate(
    account_id: int,
    payload: OpenVpnIssueCertificate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:cert:issue")),
):
    return _certificate_read(openvpn_service.issue_certificate(account_id, payload.resolved_expires_at(), actor_id=current_user.id))


@router.post("/certificates/{certificate_id}/revoke", response_model=OpenVpnCertificateRead)
def revoke_certificate(
    certificate_id: int,
    payload: OpenVpnRevokeCertificate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:cert:revoke")),
):
    return _certificate_read(openvpn_service.revoke_certificate(certificate_id, payload.reason, actor_id=current_user.id))


@router.post("/certificates/{certificate_id}/renew", response_model=OpenVpnCertificateRead)
def renew_certificate(
    certificate_id: int,
    payload: OpenVpnIssueCertificate,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:cert:renew")),
):
    return _certificate_read(openvpn_service.renew_certificate(certificate_id, payload.resolved_expires_at(), actor_id=current_user.id))


@router.get("/sessions", response_model=list[OpenVpnSessionRead])
def list_sessions(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    server_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:session:query")),
):
    return [_session_read(item, openvpn_service) for item in openvpn_service.list_sessions(skip, limit, server_id, user_id, status)]


@router.post("/sessions/{session_id}/kick", response_model=OpenVpnSessionRead)
def kick_session(
    session_id: int,
    openvpn_service: OpenVpnServiceDep,
    current_user=Depends(require_permission("ops:openvpn:session:kick")),
):
    return _session_read(openvpn_service.kick_session(session_id), openvpn_service)


@router.get("/logs", response_model=list[OpenVpnConnectionLogRead])
def list_logs(
    openvpn_service: OpenVpnServiceDep,
    skip: int = 0,
    limit: int = 100,
    server_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:log:query")),
):
    return [_log_read(item, openvpn_service) for item in openvpn_service.list_logs(skip, limit, server_id, user_id, action)]


@router.get("/logs/export", response_model=OpenVpnConfigRead)
def export_logs(
    openvpn_service: OpenVpnServiceDep,
    server_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    current_user=Depends(require_permission("ops:openvpn:log:export")),
):
    filename, content = openvpn_service.export_logs_csv(server_id=server_id, user_id=user_id, action=action)
    return {"filename": filename, "content": content}
