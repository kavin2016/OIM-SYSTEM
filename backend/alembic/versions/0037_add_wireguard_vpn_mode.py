"""Add WireGuard VPN mode

Revision ID: 0037_add_wireguard_vpn_mode
Revises: 0036_add_login_logs
Create Date: 2026-06-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0037_add_wireguard_vpn_mode"
down_revision = "0036_add_login_logs"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                  AND COLUMN_NAME = :column_name
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if not _column_exists(bind, table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    _add_column_if_missing(
        "openvpn_servers",
        sa.Column("vpn_type", sa.String(length=32), nullable=False, server_default=sa.text("'openvpn'"), comment="VPN类型：openvpn/wireguard"),
    )
    _add_column_if_missing("openvpn_servers", sa.Column("wg_interface", sa.String(length=64), nullable=True, comment="WireGuard接口名称"))
    _add_column_if_missing("openvpn_servers", sa.Column("wg_network_cidr", sa.String(length=64), nullable=True, comment="WireGuard客户端网段"))
    _add_column_if_missing("openvpn_servers", sa.Column("wg_dns", sa.String(length=255), nullable=True, comment="WireGuard客户端DNS"))
    _add_column_if_missing("openvpn_servers", sa.Column("wg_allowed_ips", sa.String(length=255), nullable=True, comment="WireGuard客户端AllowedIPs"))
    _add_column_if_missing("openvpn_servers", sa.Column("wg_persistent_keepalive", sa.Integer(), nullable=True, comment="WireGuard PersistentKeepalive"))
    _add_column_if_missing("openvpn_servers", sa.Column("wg_public_key", sa.String(length=128), nullable=True, comment="WireGuard服务器公钥"))

    _add_column_if_missing("openvpn_accounts", sa.Column("wg_client_private_key", sa.String(length=128), nullable=True, comment="WireGuard客户端私钥"))
    _add_column_if_missing("openvpn_accounts", sa.Column("wg_client_public_key", sa.String(length=128), nullable=True, comment="WireGuard客户端公钥"))
    _add_column_if_missing("openvpn_accounts", sa.Column("wg_client_address", sa.String(length=64), nullable=True, comment="WireGuard客户端地址"))


def downgrade():
    for column_name in ("wg_client_address", "wg_client_public_key", "wg_client_private_key"):
        op.drop_column("openvpn_accounts", column_name)
    for column_name in (
        "wg_public_key",
        "wg_persistent_keepalive",
        "wg_allowed_ips",
        "wg_dns",
        "wg_network_cidr",
        "wg_interface",
        "vpn_type",
    ):
        op.drop_column("openvpn_servers", column_name)
