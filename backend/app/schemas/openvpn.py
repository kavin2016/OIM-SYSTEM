from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, Field, field_validator


SERVER_STATUSES = {"online", "offline", "maintenance", "disabled"}
ACCOUNT_STATUSES = {"pending", "enabled", "disabled", "revoked"}
CERTIFICATE_STATUSES = {"issued", "expired", "revoked"}
TARGET_TYPES = {"user", "department", "role", "position"}
PROTOCOLS = {"udp", "tcp"}


class OpenVpnServerBase(BaseModel):
    name: str
    code: str
    region: Optional[str] = None
    host: str
    port: int = Field(default=1194, ge=1, le=65535)
    protocol: str = "udp"
    management_host: Optional[str] = None
    management_port: Optional[int] = Field(default=None, ge=1, le=65535)
    max_clients: int = Field(default=0, ge=0)
    current_clients: int = Field(default=0, ge=0)
    status: str = "disabled"
    is_default: bool = False
    config_template: Optional[str] = None
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


class OpenVpnServerCreate(OpenVpnServerBase):
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


class OpenVpnServerRead(OpenVpnServerBase):
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
    certificate_status: Optional[str] = None
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
