from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class OpenVpnServer(Base):
    __tablename__ = "openvpn_servers"

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN服务器ID")
    name = Column(String(100), unique=True, index=True, nullable=False, comment="服务器名称")
    code = Column(String(64), unique=True, index=True, nullable=False, comment="服务器编码")
    region = Column(String(64), nullable=True, comment="服务器区域")
    host = Column(String(255), nullable=False, comment="公网IP或域名")
    port = Column(Integer, default=1194, nullable=False, comment="VPN端口")
    protocol = Column(String(16), default="udp", nullable=False, comment="协议：udp/tcp")
    management_host = Column(String(255), nullable=True, comment="Management地址")
    management_port = Column(Integer, nullable=True, comment="Management端口")
    max_clients = Column(Integer, default=0, nullable=False, comment="最大客户端数，0=不限制")
    current_clients = Column(Integer, default=0, nullable=False, comment="当前在线数")
    status = Column(String(32), default="disabled", nullable=False, comment="状态")
    is_default = Column(Boolean, default=False, nullable=False, comment="是否默认服务器")
    config_template = Column(Text, nullable=True, comment="客户端配置模板")
    remark = Column(Text, nullable=True, comment="备注")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    accounts = relationship("OpenVpnAccount", back_populates="server")
    certificates = relationship("OpenVpnCertificate", back_populates="server")
    assignment_rules = relationship("OpenVpnAssignmentRule", back_populates="server")


class OpenVpnAssignmentRule(Base):
    __tablename__ = "openvpn_assignment_rules"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", "server_id", name="uq_openvpn_rule_target_server"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN分配规则ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="CASCADE"), nullable=False, comment="服务器ID")
    target_type = Column(String(32), nullable=False, comment="对象类型：user/department/role/position")
    target_id = Column(Integer, nullable=False, comment="对象ID")
    priority = Column(Integer, default=100, nullable=False, comment="优先级")
    fallback_enabled = Column(Boolean, default=False, nullable=False, comment="是否允许回退")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    remark = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    server = relationship("OpenVpnServer", back_populates="assignment_rules")


class OpenVpnAccount(Base):
    __tablename__ = "openvpn_accounts"

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN账号ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="用户ID")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="SET NULL"), nullable=True, comment="服务器ID")
    vpn_username = Column(String(64), unique=True, index=True, nullable=False, comment="VPN用户名")
    status = Column(String(32), default="pending", nullable=False, comment="状态")
    assign_source = Column(String(32), default="default", nullable=False, comment="分配来源")
    assignment_rule_id = Column(Integer, ForeignKey("openvpn_assignment_rules.id", ondelete="SET NULL"), nullable=True, comment="命中规则ID")
    config_version = Column(Integer, default=1, nullable=False, comment="配置版本")
    last_config_generated_at = Column(DateTime, nullable=True, comment="最近生成配置时间")
    last_connected_at = Column(DateTime, nullable=True, comment="最近连接时间")
    last_virtual_ip = Column(String(64), nullable=True, comment="最近VPN IP")
    last_real_ip = Column(String(64), nullable=True, comment="最近公网IP")
    remark = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    user = relationship("User")
    server = relationship("OpenVpnServer", back_populates="accounts")
    assignment_rule = relationship("OpenVpnAssignmentRule")
    certificates = relationship("OpenVpnCertificate", back_populates="account")


class OpenVpnCertificate(Base):
    __tablename__ = "openvpn_certificates"

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN证书ID")
    account_id = Column(Integer, ForeignKey("openvpn_accounts.id", ondelete="CASCADE"), nullable=False, comment="账号ID")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="CASCADE"), nullable=False, comment="服务器ID")
    common_name = Column(String(128), index=True, nullable=False, comment="证书CN")
    serial_number = Column(String(128), unique=True, index=True, nullable=False, comment="证书序列号")
    status = Column(String(32), default="issued", nullable=False, comment="状态")
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="签发时间")
    expires_at = Column(DateTime, nullable=False, comment="到期时间")
    revoked_at = Column(DateTime, nullable=True, comment="吊销时间")
    revoked_reason = Column(String(255), nullable=True, comment="吊销原因")
    config_file_path = Column(String(512), nullable=True, comment="配置文件路径")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    account = relationship("OpenVpnAccount", back_populates="certificates")
    server = relationship("OpenVpnServer", back_populates="certificates")


class OpenVpnSession(Base):
    __tablename__ = "openvpn_sessions"

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN会话ID")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="CASCADE"), nullable=False, comment="服务器ID")
    account_id = Column(Integer, ForeignKey("openvpn_accounts.id", ondelete="CASCADE"), nullable=True, comment="账号ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    common_name = Column(String(128), nullable=False, comment="OpenVPN CN")
    virtual_ip = Column(String(64), nullable=True, comment="VPN IP")
    real_ip = Column(String(64), nullable=True, comment="公网IP")
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="连接时间")
    disconnected_at = Column(DateTime, nullable=True, comment="断开时间")
    bytes_in = Column(Integer, default=0, nullable=False, comment="入站流量")
    bytes_out = Column(Integer, default=0, nullable=False, comment="出站流量")
    status = Column(String(32), default="online", nullable=False, comment="状态")


class OpenVpnConnectionLog(Base):
    __tablename__ = "openvpn_connection_logs"

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN连接日志ID")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="SET NULL"), nullable=True, comment="服务器ID")
    account_id = Column(Integer, ForeignKey("openvpn_accounts.id", ondelete="SET NULL"), nullable=True, comment="账号ID")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    action = Column(String(32), nullable=False, comment="动作")
    real_ip = Column(String(64), nullable=True, comment="公网IP")
    virtual_ip = Column(String(64), nullable=True, comment="VPN IP")
    result = Column(String(32), default="success", nullable=False, comment="结果")
    message = Column(Text, nullable=True, comment="日志内容")
    extra = Column(JSON, nullable=True, comment="扩展信息")
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="发生时间")
