from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
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
    certificate_backend = Column(String(32), default="metadata", nullable=False, comment="证书后端：metadata/local_easyrsa")
    ssh_host = Column(String(255), nullable=True, comment="证书服务器SSH地址")
    ssh_port = Column(Integer, nullable=True, comment="证书服务器SSH端口")
    ssh_user = Column(String(128), nullable=True, comment="证书服务器SSH用户")
    ssh_key_path = Column(String(512), nullable=True, comment="证书服务器SSH私钥路径")
    easy_rsa_dir = Column(String(512), nullable=True, comment="Easy-RSA目录")
    pki_dir = Column(String(512), nullable=True, comment="PKI目录")
    ca_cert_path = Column(String(512), nullable=True, comment="CA证书路径")
    tls_crypt_key_path = Column(String(512), nullable=True, comment="tls-crypt或ta.key路径")
    crl_path = Column(String(512), nullable=True, comment="CRL文件路径")
    client_config_dir = Column(String(512), nullable=True, comment="客户端配置输出目录")
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
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), unique=True, nullable=False, comment="用户ID")
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
    cert_path = Column(String(512), nullable=True, comment="客户端证书路径")
    key_path = Column(String(512), nullable=True, comment="客户端私钥路径")
    request_path = Column(String(512), nullable=True, comment="证书请求路径")
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
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    common_name = Column(String(128), nullable=False, comment="OpenVPN CN")
    virtual_ip = Column(String(64), nullable=True, comment="VPN IP")
    real_ip = Column(String(64), nullable=True, comment="公网IP")
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="连接时间")
    disconnected_at = Column(DateTime, nullable=True, comment="断开时间")
    bytes_in = Column(BigInteger, default=0, nullable=False, comment="入站流量")
    bytes_out = Column(BigInteger, default=0, nullable=False, comment="出站流量")
    status = Column(String(32), default="online", nullable=False, comment="状态")


class OpenVpnConnectionLog(Base):
    __tablename__ = "openvpn_connection_logs"
    __table_args__ = (
        Index("ix_openvpn_logs_server_id_id", "server_id", "id"),
        Index("ix_openvpn_logs_user_id_id", "user_id", "id"),
        Index("ix_openvpn_logs_action_id", "action", "id"),
        Index("ix_openvpn_logs_occurred_id", "occurred_at", "id"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN连接日志ID")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="SET NULL"), nullable=True, comment="服务器ID")
    account_id = Column(Integer, ForeignKey("openvpn_accounts.id", ondelete="SET NULL"), nullable=True, comment="账号ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="SET NULL"), nullable=True, comment="用户ID")
    action = Column(String(32), nullable=False, comment="动作")
    real_ip = Column(String(64), nullable=True, comment="公网IP")
    virtual_ip = Column(String(64), nullable=True, comment="VPN IP")
    result = Column(String(32), default="success", nullable=False, comment="结果")
    message = Column(Text, nullable=True, comment="日志内容")
    extra = Column(JSON, nullable=True, comment="扩展信息")
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="发生时间")


class OpenVpnTrafficRecord(Base):
    __tablename__ = "openvpn_traffic_records"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_openvpn_traffic_session"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN流量原始记录ID")
    server_id = Column(Integer, ForeignKey("openvpn_servers.id", ondelete="SET NULL"), nullable=True, index=True, comment="服务器ID")
    account_id = Column(Integer, ForeignKey("openvpn_accounts.id", ondelete="SET NULL"), nullable=True, index=True, comment="账号ID")
    certificate_id = Column(Integer, ForeignKey("openvpn_certificates.id", ondelete="SET NULL"), nullable=True, index=True, comment="证书ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="SET NULL"), nullable=True, index=True, comment="用户ID")
    department_id = Column(Integer, ForeignKey("sys_departments.id", ondelete="SET NULL"), nullable=True, index=True, comment="部门ID")
    session_id = Column(Integer, ForeignKey("openvpn_sessions.id", ondelete="SET NULL"), nullable=True, index=True, comment="会话ID")
    common_name = Column(String(128), nullable=True, index=True, comment="证书CN")
    virtual_ip = Column(String(64), nullable=True, comment="VPN IP")
    real_ip = Column(String(64), nullable=True, comment="公网IP")
    bytes_in = Column(BigInteger, default=0, nullable=False, comment="入站流量")
    bytes_out = Column(BigInteger, default=0, nullable=False, comment="出站流量")
    bytes_total = Column(BigInteger, default=0, nullable=False, comment="总流量")
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="记录时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")


class OpenVpnTrafficAggregate(Base):
    __tablename__ = "openvpn_traffic_aggregates"
    __table_args__ = (
        UniqueConstraint("period_type", "period_start", "dimension_type", "dimension_id", name="uq_openvpn_traffic_aggregate_dimension"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN流量聚合ID")
    period_type = Column(String(16), nullable=False, index=True, comment="周期：day/month")
    period_start = Column(Date, nullable=False, index=True, comment="周期开始日期")
    dimension_type = Column(String(32), nullable=False, index=True, comment="维度：server/department/certificate")
    dimension_id = Column(Integer, nullable=True, index=True, comment="维度ID")
    server_id = Column(Integer, nullable=True, index=True, comment="服务器ID")
    account_id = Column(Integer, nullable=True, index=True, comment="账号ID")
    certificate_id = Column(Integer, nullable=True, index=True, comment="证书ID")
    department_id = Column(Integer, nullable=True, index=True, comment="部门ID")
    bytes_in = Column(BigInteger, default=0, nullable=False, comment="入站流量")
    bytes_out = Column(BigInteger, default=0, nullable=False, comment="出站流量")
    bytes_total = Column(BigInteger, default=0, nullable=False, comment="总流量")
    session_count = Column(Integer, default=0, nullable=False, comment="会话数")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class OpenVpnTrafficThresholdRule(Base):
    __tablename__ = "openvpn_traffic_threshold_rules"
    __table_args__ = (
        UniqueConstraint("target_type", "target_id", "period_type", name="uq_openvpn_traffic_threshold_target"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN流量阈值规则ID")
    name = Column(String(100), nullable=False, comment="规则名称")
    target_type = Column(String(32), nullable=False, index=True, comment="对象类型：server/certificate")
    target_id = Column(Integer, nullable=False, index=True, comment="对象ID")
    period_type = Column(String(16), nullable=False, comment="周期：day/month")
    threshold_bytes = Column(BigInteger, nullable=False, comment="阈值字节数")
    action = Column(String(32), default="notify", nullable=False, comment="处理策略：notify/disable_certificate/manual_review")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    remark = Column(Text, nullable=True, comment="备注")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")


class OpenVpnTrafficAlert(Base):
    __tablename__ = "openvpn_traffic_alerts"
    __table_args__ = (
        UniqueConstraint("rule_id", "period_type", "period_start", "target_type", "target_id", name="uq_openvpn_traffic_alert_period"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="OpenVPN流量告警ID")
    rule_id = Column(Integer, ForeignKey("openvpn_traffic_threshold_rules.id", ondelete="SET NULL"), nullable=True, index=True, comment="规则ID")
    target_type = Column(String(32), nullable=False, index=True, comment="对象类型")
    target_id = Column(Integer, nullable=False, index=True, comment="对象ID")
    server_id = Column(Integer, nullable=True, index=True, comment="服务器ID")
    certificate_id = Column(Integer, nullable=True, index=True, comment="证书ID")
    account_id = Column(Integer, nullable=True, index=True, comment="账号ID")
    period_type = Column(String(16), nullable=False, comment="周期")
    period_start = Column(Date, nullable=False, index=True, comment="周期开始日期")
    threshold_bytes = Column(BigInteger, nullable=False, comment="阈值字节数")
    actual_bytes = Column(BigInteger, nullable=False, comment="实际字节数")
    action = Column(String(32), nullable=False, comment="处理策略")
    status = Column(String(32), default="open", nullable=False, index=True, comment="状态：open/processed")
    message = Column(Text, nullable=True, comment="告警内容")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    processed_by = Column(Integer, nullable=True, comment="处理人ID")
    processed_at = Column(DateTime, nullable=True, comment="处理时间")
    process_note = Column(Text, nullable=True, comment="处理说明")
