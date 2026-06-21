"""Add OpenVPN SSH Easy-RSA backend fields

Revision ID: 0031_openvpn_ssh_easyrsa
Revises: 0030_group_openvpn_menus
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0031_openvpn_ssh_easyrsa"
down_revision = "0030_group_openvpn_menus"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name, column_name):
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_column_if_missing(bind, table_name, column):
    if not _column_exists(bind, table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("ssh_host", sa.String(length=255), nullable=True, comment="证书服务器SSH地址"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("ssh_port", sa.Integer(), nullable=True, comment="证书服务器SSH端口"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("ssh_user", sa.String(length=128), nullable=True, comment="证书服务器SSH用户"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("ssh_key_path", sa.String(length=512), nullable=True, comment="证书服务器SSH私钥路径"))


def downgrade():
    bind = op.get_bind()
    for column_name in ("ssh_key_path", "ssh_user", "ssh_port", "ssh_host"):
        if _column_exists(bind, "openvpn_servers", column_name):
            op.drop_column("openvpn_servers", column_name)
