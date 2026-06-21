from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field, field_validator


SERVER_STATUSES = {"online", "offline", "maintenance", "disabled"}
ACCOUNT_STATUSES = {"pending", "enabled", "disabled", "revoked"}
CERTIFICATE_STATUSES = {"issued", "expired", "revoked"}
TARGET_TYPES = {"user", "department", "role", "position"}
PROTOCOLS = {"udp", "tcp"}
CERTIFICATE_BACKENDS = {"metadata", "local_easyrsa", "ssh_easyrsa"}
TRAFFIC_DIMENSIONS = {"server", "department", "certificate"}
TRAFFIC_PERIOD_TYPES = {"day", "month"}
TRAFFIC_THRESHOLD_TARGET_TYPES = {"server", "certificate"}
TRAFFIC_THRESHOLD_ACTIONS = {"notify", "disable_certificate", "manual_review"}
TRAFFIC_ALERT_STATUSES = {"open", "processed"}


class OpenVpnServerBase(BaseModel):
    name: str
    code: str
    region: Optional[str] = None
    host: str
    port: int = Field(default=1194, ge=1, le=65535)
    protocol: str = "udp"
    max_clients: int = Field(default=0, ge=0)
    current_clients: int = Field(default=0, ge=0)
    status: str = "disabled"
    is_default: bool = False
    remark: Optional[str] = None
    is_active: bool = True

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, value):
        value = (value or "").lower()
        if value in PROTOCOLS:
            return value
        raise ValueError("协议只能是 udp 或 tcp")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value in SERVER_STATUSES:
            return value
        raise ValueError("服务器状态不合法")


class OpenVpnServerSecretMixin(BaseModel):
    management_host: Optional[str] = None
    management_port: Optional[int] = Field(default=None, ge=1, le=65535)
    certificate_backend: str = "metadata"
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = Field(default=None, ge=1, le=65535)
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None
    easy_rsa_dir: Optional[str] = None
    pki_dir: Optional[str] = None
    ca_cert_path: Optional[str] = None
    tls_crypt_key_path: Optional[str] = None
    crl_path: Optional[str] = None
    client_config_dir: Optional[str] = None
    config_template: Optional[str] = None

    @field_validator("certificate_backend")
    @classmethod
    def validate_certificate_backend(cls, value):
        if value in CERTIFICATE_BACKENDS:
            return value
        raise ValueError("证书后端只能是 metadata、local_easyrsa 或 ssh_easyrsa")


class OpenVpnServerCreate(OpenVpnServerBase, OpenVpnServerSecretMixin):
    pass


class OpenVpnServerUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    region: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    protocol: Optional[str] = None
    management_host: Optional[str] = None
    management_port: Optional[int] = Field(default=None, ge=1, le=65535)
    max_clients: Optional[int] = Field(default=None, ge=0)
    current_clients: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None
    is_default: Optional[bool] = None
    certificate_backend: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = Field(default=None, ge=1, le=65535)
    ssh_user: Optional[str] = None
    ssh_key_path: Optional[str] = None
    easy_rsa_dir: Optional[str] = None
    pki_dir: Optional[str] = None
    ca_cert_path: Optional[str] = None
    tls_crypt_key_path: Optional[str] = None
    crl_path: Optional[str] = None
    client_config_dir: Optional[str] = None
    config_template: Optional[str] = None
    remark: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, value):
        if value is None:
            return value
        value = value.lower()
        if value in PROTOCOLS:
            return value
        raise ValueError("协议只能是 udp 或 tcp")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        if value is None or value in SERVER_STATUSES:
            return value
        raise ValueError("服务器状态不合法")

    @field_validator("certificate_backend")
    @classmethod
    def validate_certificate_backend(cls, value):
        if value is None or value in CERTIFICATE_BACKENDS:
            return value
        raise ValueError("证书后端只能是 metadata、local_easyrsa 或 ssh_easyrsa")


class OpenVpnServerRead(OpenVpnServerBase, OpenVpnServerSecretMixin):
    id: int
    is_deleted: bool
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpenVpnAssignmentRuleBase(BaseModel):
    name: str
    server_id: int
    target_type: str
    target_id: int
    priority: int = 100
    fallback_enabled: bool = False
    is_active: bool = True
    remark: Optional[str] = None

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, value):
        if value in TARGET_TYPES:
            return value
        raise ValueError("绑定对象只能是 user、department、role、position")


class OpenVpnAssignmentRuleCreate(OpenVpnAssignmentRuleBase):
    pass


class OpenVpnAssignmentRuleUpdate(BaseModel):
    name: Optional[str] = None
    server_id: Optional[int] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    priority: Optional[int] = None
    fallback_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    remark: Optional[str] = None

    @field_validator("target_type")
    @classmethod
    def validate_target_type(cls, value):
        if value is None or value in TARGET_TYPES:
            return value
        raise ValueError("绑定对象只能是 user、department、role、position")


class OpenVpnAssignmentRuleRead(OpenVpnAssignmentRuleBase):
    id: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpenVpnAccountRead(BaseModel):
    id: int
    user_id: int
    server_id: Optional[int] = None
    vpn_username: str
    status: str
    assign_source: str
    assignment_rule_id: Optional[int] = None
    config_version: int
    last_config_generated_at: Optional[datetime] = None
    last_connected_at: Optional[datetime] = None
    last_virtual_ip: Optional[str] = None
    last_real_ip: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime
    username: Optional[str] = None
    nickname: Optional[str] = None
    server_name: Optional[str] = None
    certificate_id: Optional[int] = None
    certificate_status: Optional[str] = None
    certificate_serial_number: Optional[str] = None
    certificate_expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OpenVpnEnableAccount(BaseModel):
    server_id: Optional[int] = None
    vpn_username: Optional[str] = None
    remark: Optional[str] = None


class OpenVpnAssignServer(BaseModel):
    server_id: Optional[int] = None
    refresh_config: bool = True


class OpenVpnCertificateRead(BaseModel):
    id: int
    account_id: int
    server_id: int
    common_name: str
    serial_number: str
    status: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    request_path: Optional[str] = None
    config_file_path: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    username: Optional[str] = None
    server_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OpenVpnIssueCertificate(BaseModel):
    expires_at: Optional[datetime] = None
    valid_days: int = Field(default=365, ge=1, le=3650)

    def resolved_expires_at(self) -> datetime:
        return self.expires_at or datetime.utcnow() + timedelta(days=self.valid_days)


class OpenVpnRevokeCertificate(BaseModel):
    reason: Optional[str] = None


class OpenVpnSessionRead(BaseModel):
    id: int
    server_id: int
    account_id: Optional[int] = None
    user_id: Optional[int] = None
    common_name: str
    virtual_ip: Optional[str] = None
    real_ip: Optional[str] = None
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    bytes_in: int
    bytes_out: int
    status: str
    username: Optional[str] = None
    server_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OpenVpnSessionEvent(BaseModel):
    server_code: Optional[str] = None
    server_id: Optional[int] = None
    common_name: str
    virtual_ip: Optional[str] = None
    real_ip: Optional[str] = None
    trusted_ip: Optional[str] = None
    bytes_in: int = Field(default=0, ge=0)
    bytes_out: int = Field(default=0, ge=0)
    connected_at: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    message: Optional[str] = None


class OpenVpnConnectionLogRead(BaseModel):
    id: int
    server_id: Optional[int] = None
    account_id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    real_ip: Optional[str] = None
    virtual_ip: Optional[str] = None
    result: str
    message: Optional[str] = None
    extra: Optional[dict] = None
    occurred_at: datetime
    username: Optional[str] = None
    server_name: Optional[str] = None

    model_config = {"from_attributes": True}


class OpenVpnConfigRead(BaseModel):
    filename: str
    content: str


class OpenVpnResolvedServer(BaseModel):
    server: Optional[OpenVpnServerRead] = None
    assign_source: str
    assignment_rule_id: Optional[int] = None


class OpenVpnTrafficOverview(BaseModel):
    bytes_in: int = 0
    bytes_out: int = 0
    bytes_total: int = 0
    session_count: int = 0
    open_alert_count: int = 0
    active_rule_count: int = 0


class OpenVpnTrafficMetric(BaseModel):
    dimension_type: str
    dimension_id: Optional[int] = None
    name: str
    bytes_in: int = 0
    bytes_out: int = 0
    bytes_total: int = 0
    session_count: int = 0


class OpenVpnTrafficTrendItem(BaseModel):
    period_start: date
    bytes_in: int = 0
    bytes_out: int = 0
    bytes_total: int = 0
    session_count: int = 0


class OpenVpnTrafficThresholdRuleBase(BaseModel):
    name: str
    target_type: str
    target_id: int
    period_type: str = "day"
    threshold_bytes: int = Field(ge=1)
    action: str = "notify"
    is_active: bool = True
    remark: Optional[str] = None

    @field_validator("target_type")
    @classmethod
    def validate_threshold_target_type(cls, value):
        if value in TRAFFIC_THRESHOLD_TARGET_TYPES:
            return value
        raise ValueError("阈值对象只能是 server 或 certificate")

    @field_validator("period_type")
    @classmethod
    def validate_period_type(cls, value):
        if value in TRAFFIC_PERIOD_TYPES:
            return value
        raise ValueError("统计周期只能是 day 或 month")

    @field_validator("action")
    @classmethod
    def validate_threshold_action(cls, value):
        if value in TRAFFIC_THRESHOLD_ACTIONS:
            return value
        raise ValueError("超限策略只能是 notify、disable_certificate 或 manual_review")


class OpenVpnTrafficThresholdRuleCreate(OpenVpnTrafficThresholdRuleBase):
    pass


class OpenVpnTrafficThresholdRuleUpdate(BaseModel):
    name: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    period_type: Optional[str] = None
    threshold_bytes: Optional[int] = Field(default=None, ge=1)
    action: Optional[str] = None
    is_active: Optional[bool] = None
    remark: Optional[str] = None

    @field_validator("target_type")
    @classmethod
    def validate_threshold_target_type(cls, value):
        if value is None or value in TRAFFIC_THRESHOLD_TARGET_TYPES:
            return value
        raise ValueError("阈值对象只能是 server 或 certificate")

    @field_validator("period_type")
    @classmethod
    def validate_period_type(cls, value):
        if value is None or value in TRAFFIC_PERIOD_TYPES:
            return value
        raise ValueError("统计周期只能是 day 或 month")

    @field_validator("action")
    @classmethod
    def validate_threshold_action(cls, value):
        if value is None or value in TRAFFIC_THRESHOLD_ACTIONS:
            return value
        raise ValueError("超限策略只能是 notify、disable_certificate 或 manual_review")


class OpenVpnTrafficThresholdRuleRead(OpenVpnTrafficThresholdRuleBase):
    id: int
    target_name: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime
    updated_by: Optional[int] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class OpenVpnTrafficAlertRead(BaseModel):
    id: int
    rule_id: Optional[int] = None
    target_type: str
    target_id: int
    target_name: Optional[str] = None
    server_id: Optional[int] = None
    server_name: Optional[str] = None
    certificate_id: Optional[int] = None
    account_id: Optional[int] = None
    username: Optional[str] = None
    period_type: str
    period_start: date
    threshold_bytes: int
    actual_bytes: int
    action: str
    status: str
    message: Optional[str] = None
    created_at: datetime
    processed_by: Optional[int] = None
    processed_at: Optional[datetime] = None
    process_note: Optional[str] = None

    model_config = {"from_attributes": True}


class OpenVpnTrafficAlertProcess(BaseModel):
    note: Optional[str] = None
