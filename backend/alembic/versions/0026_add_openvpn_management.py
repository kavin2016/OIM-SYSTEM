"""Add OpenVPN management

Revision ID: 0026_add_openvpn_management
Revises: 0025_remove_telegram_attendance
Create Date: 2026-06-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0026_add_openvpn_management"
down_revision = "0025_remove_telegram_attendance"
branch_labels = None
depends_on = None


OPENVPN_PERMISSIONS = [
    {
        "name": "运维管理",
        "code": "ops",
        "type": "menu",
        "path": "/ops",
        "component": None,
        "icon": "monitor",
        "sort_order": 300,
        "description": "运维管理一级菜单",
        "children": [
            {
                "name": "OpenVPN管理",
                "code": "ops:openvpn:list",
                "type": "menu",
                "path": "/ops/openvpn",
                "component": "OpenVpnManagement",
                "icon": "connection",
                "sort_order": 301,
                "description": "OpenVPN管理",
                "children": [
                    ("服务器查询", "ops:openvpn:server:query", "查询OpenVPN服务器"),
                    ("服务器新增", "ops:openvpn:server:create", "新增OpenVPN服务器"),
                    ("服务器修改", "ops:openvpn:server:update", "修改OpenVPN服务器"),
                    ("服务器删除", "ops:openvpn:server:delete", "删除OpenVPN服务器"),
                    ("服务器测试", "ops:openvpn:server:test", "测试OpenVPN服务器连接"),
                    ("设为默认服务器", "ops:openvpn:server:set-default", "设置默认OpenVPN服务器"),
                    ("账号查询", "ops:openvpn:account:query", "查询OpenVPN账号"),
                    ("账号开通", "ops:openvpn:account:enable", "开通OpenVPN账号"),
                    ("账号禁用", "ops:openvpn:account:disable", "禁用OpenVPN账号"),
                    ("账号分配服务器", "ops:openvpn:account:assign-server", "分配OpenVPN服务器"),
                    ("下载配置", "ops:openvpn:account:download-config", "下载OpenVPN客户端配置"),
                    ("证书查询", "ops:openvpn:cert:query", "查询OpenVPN证书"),
                    ("证书签发", "ops:openvpn:cert:issue", "签发OpenVPN证书"),
                    ("证书吊销", "ops:openvpn:cert:revoke", "吊销OpenVPN证书"),
                    ("证书续期", "ops:openvpn:cert:renew", "续期OpenVPN证书"),
                    ("会话查询", "ops:openvpn:session:query", "查询OpenVPN在线会话"),
                    ("会话下线", "ops:openvpn:session:kick", "强制OpenVPN会话下线"),
                    ("日志查询", "ops:openvpn:log:query", "查询OpenVPN连接日志"),
                    ("日志导出", "ops:openvpn:log:export", "导出OpenVPN连接日志"),
                    ("分配规则查询", "ops:openvpn:rule:query", "查询OpenVPN分配规则"),
                    ("分配规则新增", "ops:openvpn:rule:create", "新增OpenVPN分配规则"),
                    ("分配规则修改", "ops:openvpn:rule:update", "修改OpenVPN分配规则"),
                    ("分配规则删除", "ops:openvpn:rule:delete", "删除OpenVPN分配规则"),
                ],
            }
        ],
    }
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).scalar()


def _insert_or_update_permission(bind, item, parent_id=None):
    existing_id = _permission_id(bind, item["code"])
    values = {
        "parent_id": parent_id,
        "name": item["name"],
        "code": item["code"],
        "type": item["type"],
        "path": item.get("path"),
        "component": item.get("component"),
        "icon": item.get("icon"),
        "sort_order": item["sort_order"],
        "description": item.get("description"),
        "is_active": True,
        "is_deleted": False,
    }
    if existing_id:
        bind.execute(
            sa.text(
                """
                UPDATE permissions
                SET parent_id = :parent_id,
                    name = :name,
                    type = :type,
                    path = :path,
                    component = :component,
                    icon = :icon,
                    sort_order = :sort_order,
                    description = :description,
                    is_active = :is_active,
                    is_deleted = :is_deleted
                WHERE id = :id
                """
            ),
            {**values, "id": existing_id},
        )
        permission_id = existing_id
    else:
        result = bind.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (parent_id, name, code, type, path, component, icon, sort_order, description, is_active, is_deleted)
                VALUES
                    (:parent_id, :name, :code, :type, :path, :component, :icon, :sort_order, :description, :is_active, :is_deleted)
                """
            ),
            values,
        )
        permission_id = result.lastrowid

    for index, child in enumerate(item.get("children", []), start=1):
        if isinstance(child, dict):
            _insert_or_update_permission(bind, child, permission_id)
        else:
            child_item = {
                "name": child[0],
                "code": child[1],
                "type": "button",
                "path": None,
                "component": None,
                "icon": None,
                "sort_order": item["sort_order"] * 10 + index,
                "description": child[2],
            }
            _insert_or_update_permission(bind, child_item, permission_id)

    return permission_id


def _collect_permission_codes(items):
    codes = []
    for item in items:
        codes.append(item["code"])
        for child in item.get("children", []):
            if isinstance(child, dict):
                codes.extend(_collect_permission_codes([child]))
            else:
                codes.append(child[1])
    return codes


def _grant_to_admin_role(bind, codes):
    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = :code AND is_deleted = 0"),
        {"code": "admin"},
    ).scalar()
    if not admin_role_id:
        return
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM permissions WHERE code IN :codes"),
            {"codes": tuple(codes)},
        )
    ]
    for permission_id in permission_ids:
        exists = bind.execute(
            sa.text(
                """
                SELECT id FROM role_permissions
                WHERE role_id = :role_id AND permission_id = :permission_id
                """
            ),
            {"role_id": admin_role_id, "permission_id": permission_id},
        ).scalar()
        if not exists:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id, created_at)
                    VALUES (:role_id, :permission_id, CURRENT_TIMESTAMP)
                    """
                ),
                {"role_id": admin_role_id, "permission_id": permission_id},
            )


def upgrade():
    op.create_table(
        "openvpn_servers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="OpenVPN服务器ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="服务器名称"),
        sa.Column("code", sa.String(length=64), nullable=False, comment="服务器编码"),
        sa.Column("region", sa.String(length=64), nullable=True, comment="服务器区域"),
        sa.Column("host", sa.String(length=255), nullable=False, comment="公网IP或域名"),
        sa.Column("port", sa.Integer(), nullable=False, server_default=sa.text("1194"), comment="VPN端口"),
        sa.Column("protocol", sa.String(length=16), nullable=False, server_default=sa.text("'udp'"), comment="协议"),
        sa.Column("management_host", sa.String(length=255), nullable=True, comment="Management地址"),
        sa.Column("management_port", sa.Integer(), nullable=True, comment="Management端口"),
        sa.Column("max_clients", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="最大客户端数"),
        sa.Column("current_clients", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="当前在线数"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'disabled'"), comment="状态"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否默认服务器"),
        sa.Column("config_template", sa.Text(), nullable=True, comment="客户端配置模板"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否删除"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="修改人ID"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="修改时间"),
        sa.UniqueConstraint("name", name="uq_openvpn_servers_name"),
        sa.UniqueConstraint("code", name="uq_openvpn_servers_code"),
    )
    op.create_index("ix_openvpn_servers_status", "openvpn_servers", ["status"])
    op.create_index("ix_openvpn_servers_is_deleted", "openvpn_servers", ["is_deleted"])
    op.create_index("ix_openvpn_servers_is_default", "openvpn_servers", ["is_default"])

    op.create_table(
        "openvpn_assignment_rules",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="OpenVPN分配规则ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="规则名称"),
        sa.Column("server_id", sa.Integer(), nullable=False, comment="服务器ID"),
        sa.Column("target_type", sa.String(length=32), nullable=False, comment="对象类型"),
        sa.Column("target_id", sa.Integer(), nullable=False, comment="对象ID"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100"), comment="优先级"),
        sa.Column("fallback_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否允许回退"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="修改人ID"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="修改时间"),
        sa.ForeignKeyConstraint(["server_id"], ["openvpn_servers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("target_type", "target_id", "server_id", name="uq_openvpn_rule_target_server"),
    )
    op.create_index("ix_openvpn_rules_server_id", "openvpn_assignment_rules", ["server_id"])
    op.create_index("ix_openvpn_rules_target", "openvpn_assignment_rules", ["target_type", "target_id"])
    op.create_index("ix_openvpn_rules_active_priority", "openvpn_assignment_rules", ["is_active", "priority"])

    op.create_table(
        "openvpn_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="OpenVPN账号ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("server_id", sa.Integer(), nullable=True, comment="服务器ID"),
        sa.Column("vpn_username", sa.String(length=64), nullable=False, comment="VPN用户名"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'"), comment="状态"),
        sa.Column("assign_source", sa.String(length=32), nullable=False, server_default=sa.text("'default'"), comment="分配来源"),
        sa.Column("assignment_rule_id", sa.Integer(), nullable=True, comment="命中规则ID"),
        sa.Column("config_version", sa.Integer(), nullable=False, server_default=sa.text("1"), comment="配置版本"),
        sa.Column("last_config_generated_at", sa.DateTime(), nullable=True, comment="最近生成配置时间"),
        sa.Column("last_connected_at", sa.DateTime(), nullable=True, comment="最近连接时间"),
        sa.Column("last_virtual_ip", sa.String(length=64), nullable=True, comment="最近VPN IP"),
        sa.Column("last_real_ip", sa.String(length=64), nullable=True, comment="最近公网IP"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="修改人ID"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="修改时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["openvpn_servers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignment_rule_id"], ["openvpn_assignment_rules.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", name="uq_openvpn_accounts_user_id"),
        sa.UniqueConstraint("vpn_username", name="uq_openvpn_accounts_vpn_username"),
    )
    op.create_index("ix_openvpn_accounts_server_id", "openvpn_accounts", ["server_id"])
    op.create_index("ix_openvpn_accounts_status", "openvpn_accounts", ["status"])

    op.create_table(
        "openvpn_certificates",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="OpenVPN证书ID"),
        sa.Column("account_id", sa.Integer(), nullable=False, comment="账号ID"),
        sa.Column("server_id", sa.Integer(), nullable=False, comment="服务器ID"),
        sa.Column("common_name", sa.String(length=128), nullable=False, comment="证书CN"),
        sa.Column("serial_number", sa.String(length=128), nullable=False, comment="证书序列号"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'issued'"), comment="状态"),
        sa.Column("issued_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="签发时间"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="到期时间"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True, comment="吊销时间"),
        sa.Column("revoked_reason", sa.String(length=255), nullable=True, comment="吊销原因"),
        sa.Column("config_file_path", sa.String(length=512), nullable=True, comment="配置文件路径"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(["account_id"], ["openvpn_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["server_id"], ["openvpn_servers.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("serial_number", name="uq_openvpn_certificates_serial_number"),
    )
    op.create_index("ix_openvpn_certificates_account_id", "openvpn_certificates", ["account_id"])
    op.create_index("ix_openvpn_certificates_server_id", "openvpn_certificates", ["server_id"])
    op.create_index("ix_openvpn_certificates_common_name", "openvpn_certificates", ["common_name"])
    op.create_index("ix_openvpn_certificates_status", "openvpn_certificates", ["status"])
    op.create_index("ix_openvpn_certificates_expires_at", "openvpn_certificates", ["expires_at"])

    op.create_table(
        "openvpn_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="OpenVPN会话ID"),
        sa.Column("server_id", sa.Integer(), nullable=False, comment="服务器ID"),
        sa.Column("account_id", sa.Integer(), nullable=True, comment="账号ID"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="用户ID"),
        sa.Column("common_name", sa.String(length=128), nullable=False, comment="OpenVPN CN"),
        sa.Column("virtual_ip", sa.String(length=64), nullable=True, comment="VPN IP"),
        sa.Column("real_ip", sa.String(length=64), nullable=True, comment="公网IP"),
        sa.Column("connected_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="连接时间"),
        sa.Column("disconnected_at", sa.DateTime(), nullable=True, comment="断开时间"),
        sa.Column("bytes_in", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="入站流量"),
        sa.Column("bytes_out", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="出站流量"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'online'"), comment="状态"),
        sa.ForeignKeyConstraint(["server_id"], ["openvpn_servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["openvpn_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_openvpn_sessions_server_id", "openvpn_sessions", ["server_id"])
    op.create_index("ix_openvpn_sessions_account_id", "openvpn_sessions", ["account_id"])
    op.create_index("ix_openvpn_sessions_user_id", "openvpn_sessions", ["user_id"])
    op.create_index("ix_openvpn_sessions_status", "openvpn_sessions", ["status"])

    op.create_table(
        "openvpn_connection_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="OpenVPN连接日志ID"),
        sa.Column("server_id", sa.Integer(), nullable=True, comment="服务器ID"),
        sa.Column("account_id", sa.Integer(), nullable=True, comment="账号ID"),
        sa.Column("user_id", sa.Integer(), nullable=True, comment="用户ID"),
        sa.Column("action", sa.String(length=32), nullable=False, comment="动作"),
        sa.Column("real_ip", sa.String(length=64), nullable=True, comment="公网IP"),
        sa.Column("virtual_ip", sa.String(length=64), nullable=True, comment="VPN IP"),
        sa.Column("result", sa.String(length=32), nullable=False, server_default=sa.text("'success'"), comment="结果"),
        sa.Column("message", sa.Text(), nullable=True, comment="日志内容"),
        sa.Column("extra", sa.JSON(), nullable=True, comment="扩展信息"),
        sa.Column("occurred_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="发生时间"),
        sa.ForeignKeyConstraint(["server_id"], ["openvpn_servers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["account_id"], ["openvpn_accounts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_openvpn_logs_server_id", "openvpn_connection_logs", ["server_id"])
    op.create_index("ix_openvpn_logs_account_id", "openvpn_connection_logs", ["account_id"])
    op.create_index("ix_openvpn_logs_user_id", "openvpn_connection_logs", ["user_id"])
    op.create_index("ix_openvpn_logs_action", "openvpn_connection_logs", ["action"])
    op.create_index("ix_openvpn_logs_occurred_at", "openvpn_connection_logs", ["occurred_at"])

    bind = op.get_bind()
    for permission in OPENVPN_PERMISSIONS:
        _insert_or_update_permission(bind, permission)
    _grant_to_admin_role(bind, _collect_permission_codes(OPENVPN_PERMISSIONS))


def downgrade():
    bind = op.get_bind()
    codes = _collect_permission_codes(OPENVPN_PERMISSIONS)
    permission_ids = [
        row[0]
        for row in bind.execute(sa.text("SELECT id FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})
    ]
    if permission_ids:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id IN :ids"), {"ids": tuple(permission_ids)})
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})

    op.drop_index("ix_openvpn_logs_occurred_at", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_action", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_user_id", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_account_id", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_server_id", table_name="openvpn_connection_logs")
    op.drop_table("openvpn_connection_logs")

    op.drop_index("ix_openvpn_sessions_status", table_name="openvpn_sessions")
    op.drop_index("ix_openvpn_sessions_user_id", table_name="openvpn_sessions")
    op.drop_index("ix_openvpn_sessions_account_id", table_name="openvpn_sessions")
    op.drop_index("ix_openvpn_sessions_server_id", table_name="openvpn_sessions")
    op.drop_table("openvpn_sessions")

    op.drop_index("ix_openvpn_certificates_expires_at", table_name="openvpn_certificates")
    op.drop_index("ix_openvpn_certificates_status", table_name="openvpn_certificates")
    op.drop_index("ix_openvpn_certificates_common_name", table_name="openvpn_certificates")
    op.drop_index("ix_openvpn_certificates_server_id", table_name="openvpn_certificates")
    op.drop_index("ix_openvpn_certificates_account_id", table_name="openvpn_certificates")
    op.drop_table("openvpn_certificates")

    op.drop_index("ix_openvpn_accounts_status", table_name="openvpn_accounts")
    op.drop_index("ix_openvpn_accounts_server_id", table_name="openvpn_accounts")
    op.drop_table("openvpn_accounts")

    op.drop_index("ix_openvpn_rules_active_priority", table_name="openvpn_assignment_rules")
    op.drop_index("ix_openvpn_rules_target", table_name="openvpn_assignment_rules")
    op.drop_index("ix_openvpn_rules_server_id", table_name="openvpn_assignment_rules")
    op.drop_table("openvpn_assignment_rules")

    op.drop_index("ix_openvpn_servers_is_default", table_name="openvpn_servers")
    op.drop_index("ix_openvpn_servers_is_deleted", table_name="openvpn_servers")
    op.drop_index("ix_openvpn_servers_status", table_name="openvpn_servers")
    op.drop_table("openvpn_servers")
