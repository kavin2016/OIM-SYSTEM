"""Update VPN menu labels and paths

Revision ID: 0038_update_vpn_menu_paths
Revises: 0037_add_wireguard_vpn_mode
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0038_update_vpn_menu_paths"
down_revision = "0037_add_wireguard_vpn_mode"
branch_labels = None
depends_on = None


MENU_UPDATES = [
    ("ops:openvpn:list", "VPN管理", "/ops/vpn", None, "VPN管理"),
    ("ops:openvpn:server:list", "VPN服务器管理", "/ops/vpn/servers", "OpenVpnServerManagement", "VPN服务器管理"),
    ("ops:openvpn:account:list", "VPN用户管理", "/ops/vpn/accounts", "OpenVpnAccountManagement", "VPN用户管理"),
    ("ops:openvpn:session:list", "VPN在线会话", "/ops/vpn/sessions", "OpenVpnSessionManagement", "VPN在线会话"),
    ("ops:openvpn:log:list", "VPN连接日志", "/ops/vpn/logs", "OpenVpnLogManagement", "VPN连接日志"),
    ("ops:openvpn:rule:list", "VPN分配策略", "/ops/vpn/rules", "OpenVpnRuleManagement", "VPN分配策略"),
    ("ops:openvpn:traffic:list", "VPN流量统计", "/ops/vpn/traffic", "OpenVpnTrafficManagement", "VPN流量统计与阈值告警"),
]

PERMISSION_UPDATES = [
    ("ops:openvpn:server:query", "服务器查询", "查询VPN服务器"),
    ("ops:openvpn:server:create", "服务器新增", "新增VPN服务器"),
    ("ops:openvpn:server:update", "服务器修改", "修改VPN服务器"),
    ("ops:openvpn:server:delete", "服务器删除", "删除VPN服务器"),
    ("ops:openvpn:server:test", "服务器测试", "测试VPN服务器连接"),
    ("ops:openvpn:server:set-default", "设为默认服务器", "设置默认VPN服务器"),
    ("ops:openvpn:account:query", "账号查询", "查询VPN账号"),
    ("ops:openvpn:account:enable", "账号开通", "开通VPN账号"),
    ("ops:openvpn:account:disable", "账号禁用", "禁用VPN账号"),
    ("ops:openvpn:account:revoke", "账号吊销", "吊销VPN账号"),
    ("ops:openvpn:account:assign-server", "账号分配服务器", "分配VPN服务器"),
    ("ops:openvpn:account:download-config", "下载配置", "下载VPN客户端配置"),
    ("ops:openvpn:cert:query", "凭据查询", "查询VPN凭据"),
    ("ops:openvpn:cert:issue", "凭据签发", "签发VPN凭据"),
    ("ops:openvpn:cert:revoke", "凭据吊销", "吊销VPN凭据"),
    ("ops:openvpn:cert:renew", "凭据续期", "续期VPN凭据"),
    ("ops:openvpn:session:query", "会话查询", "查询VPN在线会话"),
    ("ops:openvpn:session:kick", "会话下线", "强制VPN会话下线"),
    ("ops:openvpn:log:query", "日志查询", "查询VPN连接日志"),
    ("ops:openvpn:log:export", "日志导出", "导出VPN连接日志"),
    ("ops:openvpn:rule:query", "分配规则查询", "查询VPN分配规则"),
    ("ops:openvpn:rule:create", "分配规则新增", "新增VPN分配规则"),
    ("ops:openvpn:rule:update", "分配规则修改", "修改VPN分配规则"),
    ("ops:openvpn:rule:delete", "分配规则删除", "删除VPN分配规则"),
    ("ops:openvpn:traffic:query", "流量查询", "查看VPN流量统计"),
    ("ops:openvpn:traffic:threshold:query", "阈值查询", "查看VPN流量阈值规则"),
    ("ops:openvpn:traffic:threshold:create", "阈值新增", "新增VPN流量阈值规则"),
    ("ops:openvpn:traffic:threshold:update", "阈值修改", "修改VPN流量阈值规则"),
    ("ops:openvpn:traffic:threshold:delete", "阈值删除", "删除VPN流量阈值规则"),
    ("ops:openvpn:traffic:alert:query", "告警查询", "查看VPN流量告警"),
    ("ops:openvpn:traffic:alert:process", "告警处理", "处理VPN流量告警"),
]

OLD_MENU_UPDATES = [
    ("ops:openvpn:list", "OpenVPN管理", "/ops/openvpn", None, "OpenVPN管理"),
    ("ops:openvpn:server:list", "OpenVPN服务器管理", "/ops/openvpn/servers", "OpenVpnServerManagement", "OpenVPN服务器管理"),
    ("ops:openvpn:account:list", "OpenVPN用户管理", "/ops/openvpn/accounts", "OpenVpnAccountManagement", "OpenVPN用户管理"),
    ("ops:openvpn:session:list", "OpenVPN在线会话", "/ops/openvpn/sessions", "OpenVpnSessionManagement", "OpenVPN在线会话"),
    ("ops:openvpn:log:list", "OpenVPN连接日志", "/ops/openvpn/logs", "OpenVpnLogManagement", "OpenVPN连接日志"),
    ("ops:openvpn:rule:list", "OpenVPN分配策略", "/ops/openvpn/rules", "OpenVpnRuleManagement", "OpenVPN分配策略"),
    ("ops:openvpn:traffic:list", "OpenVPN流量统计", "/ops/openvpn/traffic", "OpenVpnTrafficManagement", "OpenVPN流量统计与阈值告警"),
]


def _table_exists(bind, table_name):
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                """
            ),
            {"table_name": table_name},
        ).scalar()
    )


def _update_menu(bind, item):
    code, name, path, component, description = item
    bind.execute(
        sa.text(
            """
            UPDATE sys_permissions
            SET name = :name,
                path = :path,
                component = :component,
                description = :description,
                is_active = 1,
                is_deleted = 0
            WHERE code = :code
            """
        ),
        {"code": code, "name": name, "path": path, "component": component, "description": description},
    )


def _update_permission(bind, item):
    code, name, description = item
    bind.execute(
        sa.text(
            """
            UPDATE sys_permissions
            SET name = :name,
                description = :description,
                is_active = 1,
                is_deleted = 0
            WHERE code = :code
            """
        ),
        {"code": code, "name": name, "description": description},
    )


def upgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "sys_permissions"):
        return
    for item in MENU_UPDATES:
        _update_menu(bind, item)
    for item in PERMISSION_UPDATES:
        _update_permission(bind, item)


def downgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "sys_permissions"):
        return
    for item in OLD_MENU_UPDATES:
        _update_menu(bind, item)
