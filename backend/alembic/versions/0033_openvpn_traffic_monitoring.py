"""Add OpenVPN traffic monitoring

Revision ID: 0033_openvpn_traffic_monitoring
Revises: 0032_openvpn_account_revoke
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import bindparam


revision = "0033_openvpn_traffic_monitoring"
down_revision = "0032_openvpn_account_revoke"
branch_labels = None
depends_on = None


MENU_CODE = "ops:openvpn:traffic:list"
PERMISSIONS = [
    ("流量查询", "ops:openvpn:traffic:query", 1, "查看OpenVPN流量统计"),
    ("阈值查询", "ops:openvpn:traffic:threshold:query", 2, "查看OpenVPN流量阈值规则"),
    ("阈值新增", "ops:openvpn:traffic:threshold:create", 3, "新增OpenVPN流量阈值规则"),
    ("阈值修改", "ops:openvpn:traffic:threshold:update", 4, "修改OpenVPN流量阈值规则"),
    ("阈值删除", "ops:openvpn:traffic:threshold:delete", 5, "删除OpenVPN流量阈值规则"),
    ("告警查询", "ops:openvpn:traffic:alert:query", 6, "查看OpenVPN流量告警"),
    ("告警处理", "ops:openvpn:traffic:alert:process", 7, "处理OpenVPN流量告警"),
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM sys_permissions WHERE code = :code"), {"code": code}).scalar()


def _insert_or_update_permission(bind, values):
    permission_id = _permission_id(bind, values["code"])
    if permission_id:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
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
            {**values, "id": permission_id},
        )
        return permission_id

    result = bind.execute(
        sa.text(
            """
            INSERT INTO sys_permissions
                (parent_id, name, code, type, path, component, icon, sort_order, description, is_active, is_deleted)
            VALUES
                (:parent_id, :name, :code, :type, :path, :component, :icon, :sort_order, :description, :is_active, :is_deleted)
            """
        ),
        values,
    )
    return result.lastrowid


def _grant_to_existing_roles(bind, permission_id, source_codes):
    source_ids = [item for item in (_permission_id(bind, code) for code in source_codes) if item]
    if not permission_id or not source_ids:
        return
    bind.execute(
        sa.text(
            """
            INSERT INTO sys_role_permissions (role_id, permission_id, created_at)
            SELECT DISTINCT rp.role_id, :permission_id, CURRENT_TIMESTAMP
            FROM sys_role_permissions rp
            WHERE rp.permission_id IN :source_ids
              AND NOT EXISTS (
                SELECT 1
                FROM sys_role_permissions existing
                WHERE existing.role_id = rp.role_id
                  AND existing.permission_id = :permission_id
              )
            """
        ).bindparams(bindparam("source_ids", expanding=True)),
        {"permission_id": permission_id, "source_ids": tuple(source_ids)},
    )


def upgrade():
    op.alter_column("openvpn_sessions", "bytes_in", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)
    op.alter_column("openvpn_sessions", "bytes_out", existing_type=sa.Integer(), type_=sa.BigInteger(), existing_nullable=False)

    op.create_table(
        "openvpn_traffic_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, comment="OpenVPN流量原始记录ID"),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("openvpn_servers.id", ondelete="SET NULL"), nullable=True, index=True, comment="服务器ID"),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("openvpn_accounts.id", ondelete="SET NULL"), nullable=True, index=True, comment="账号ID"),
        sa.Column("certificate_id", sa.Integer(), sa.ForeignKey("openvpn_certificates.id", ondelete="SET NULL"), nullable=True, index=True, comment="证书ID"),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("sys_users.id", ondelete="SET NULL"), nullable=True, index=True, comment="用户ID"),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("sys_departments.id", ondelete="SET NULL"), nullable=True, index=True, comment="部门ID"),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("openvpn_sessions.id", ondelete="SET NULL"), nullable=True, index=True, comment="会话ID"),
        sa.Column("common_name", sa.String(length=128), nullable=True, index=True, comment="证书CN"),
        sa.Column("virtual_ip", sa.String(length=64), nullable=True, comment="VPN IP"),
        sa.Column("real_ip", sa.String(length=64), nullable=True, comment="公网IP"),
        sa.Column("bytes_in", sa.BigInteger(), nullable=False, server_default="0", comment="入站流量"),
        sa.Column("bytes_out", sa.BigInteger(), nullable=False, server_default="0", comment="出站流量"),
        sa.Column("bytes_total", sa.BigInteger(), nullable=False, server_default="0", comment="总流量"),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, index=True, comment="记录时间"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.UniqueConstraint("session_id", name="uq_openvpn_traffic_session"),
    )
    op.create_table(
        "openvpn_traffic_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, comment="OpenVPN流量聚合ID"),
        sa.Column("period_type", sa.String(length=16), nullable=False, index=True, comment="周期：day/month"),
        sa.Column("period_start", sa.Date(), nullable=False, index=True, comment="周期开始日期"),
        sa.Column("dimension_type", sa.String(length=32), nullable=False, index=True, comment="维度：server/department/certificate"),
        sa.Column("dimension_id", sa.Integer(), nullable=True, index=True, comment="维度ID"),
        sa.Column("server_id", sa.Integer(), nullable=True, index=True, comment="服务器ID"),
        sa.Column("account_id", sa.Integer(), nullable=True, index=True, comment="账号ID"),
        sa.Column("certificate_id", sa.Integer(), nullable=True, index=True, comment="证书ID"),
        sa.Column("department_id", sa.Integer(), nullable=True, index=True, comment="部门ID"),
        sa.Column("bytes_in", sa.BigInteger(), nullable=False, server_default="0", comment="入站流量"),
        sa.Column("bytes_out", sa.BigInteger(), nullable=False, server_default="0", comment="出站流量"),
        sa.Column("bytes_total", sa.BigInteger(), nullable=False, server_default="0", comment="总流量"),
        sa.Column("session_count", sa.Integer(), nullable=False, server_default="0", comment="会话数"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.UniqueConstraint("period_type", "period_start", "dimension_type", "dimension_id", name="uq_openvpn_traffic_aggregate_dimension"),
    )
    op.create_table(
        "openvpn_traffic_threshold_rules",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, comment="OpenVPN流量阈值规则ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="规则名称"),
        sa.Column("target_type", sa.String(length=32), nullable=False, index=True, comment="对象类型：server/certificate"),
        sa.Column("target_id", sa.Integer(), nullable=False, index=True, comment="对象ID"),
        sa.Column("period_type", sa.String(length=16), nullable=False, comment="周期：day/month"),
        sa.Column("threshold_bytes", sa.BigInteger(), nullable=False, comment="阈值字节数"),
        sa.Column("action", sa.String(length=32), nullable=False, server_default="notify", comment="处理策略"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1"), comment="是否启用"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="修改人ID"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="修改时间"),
        sa.UniqueConstraint("target_type", "target_id", "period_type", name="uq_openvpn_traffic_threshold_target"),
    )
    op.create_table(
        "openvpn_traffic_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True, comment="OpenVPN流量告警ID"),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("openvpn_traffic_threshold_rules.id", ondelete="SET NULL"), nullable=True, index=True, comment="规则ID"),
        sa.Column("target_type", sa.String(length=32), nullable=False, index=True, comment="对象类型"),
        sa.Column("target_id", sa.Integer(), nullable=False, index=True, comment="对象ID"),
        sa.Column("server_id", sa.Integer(), nullable=True, index=True, comment="服务器ID"),
        sa.Column("certificate_id", sa.Integer(), nullable=True, index=True, comment="证书ID"),
        sa.Column("account_id", sa.Integer(), nullable=True, index=True, comment="账号ID"),
        sa.Column("period_type", sa.String(length=16), nullable=False, comment="周期"),
        sa.Column("period_start", sa.Date(), nullable=False, index=True, comment="周期开始日期"),
        sa.Column("threshold_bytes", sa.BigInteger(), nullable=False, comment="阈值字节数"),
        sa.Column("actual_bytes", sa.BigInteger(), nullable=False, comment="实际字节数"),
        sa.Column("action", sa.String(length=32), nullable=False, comment="处理策略"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open", index=True, comment="状态"),
        sa.Column("message", sa.Text(), nullable=True, comment="告警内容"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("processed_by", sa.Integer(), nullable=True, comment="处理人ID"),
        sa.Column("processed_at", sa.DateTime(), nullable=True, comment="处理时间"),
        sa.Column("process_note", sa.Text(), nullable=True, comment="处理说明"),
        sa.UniqueConstraint("rule_id", "period_type", "period_start", "target_type", "target_id", name="uq_openvpn_traffic_alert_period"),
    )

    bind = op.get_bind()
    parent_id = _permission_id(bind, "ops:openvpn:list")
    menu_id = _insert_or_update_permission(
        bind,
        {
            "parent_id": parent_id,
            "name": "OpenVPN流量统计",
            "code": MENU_CODE,
            "type": "menu",
            "path": "/ops/openvpn/traffic",
            "component": "OpenVpnTrafficManagement",
            "icon": "data-line",
            "sort_order": 6,
            "description": "OpenVPN流量统计与阈值告警",
            "is_active": True,
            "is_deleted": False,
        },
    )
    _grant_to_existing_roles(bind, menu_id, ["ops:openvpn:session:query", "ops:openvpn:log:query", "ops:openvpn:list"])

    for name, code, sort_order, description in PERMISSIONS:
        permission_id = _insert_or_update_permission(
            bind,
            {
                "parent_id": menu_id,
                "name": name,
                "code": code,
                "type": "button",
                "path": None,
                "component": None,
                "icon": None,
                "sort_order": sort_order,
                "description": description,
                "is_active": True,
                "is_deleted": False,
            },
        )
        _grant_to_existing_roles(bind, permission_id, ["ops:openvpn:session:query", "ops:openvpn:log:query", "ops:openvpn:server:query"])


def downgrade():
    bind = op.get_bind()
    codes = [MENU_CODE, *[item[1] for item in PERMISSIONS]]
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM sys_permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
            {"codes": tuple(codes)},
        )
    ]
    if permission_ids:
        bind.execute(
            sa.text("DELETE FROM sys_role_permissions WHERE permission_id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(permission_ids)},
        )
        bind.execute(
            sa.text("DELETE FROM sys_permissions WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(permission_ids)},
        )
    op.drop_table("openvpn_traffic_alerts")
    op.drop_table("openvpn_traffic_threshold_rules")
    op.drop_table("openvpn_traffic_aggregates")
    op.drop_table("openvpn_traffic_records")
    op.alter_column("openvpn_sessions", "bytes_out", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
    op.alter_column("openvpn_sessions", "bytes_in", existing_type=sa.BigInteger(), type_=sa.Integer(), existing_nullable=False)
