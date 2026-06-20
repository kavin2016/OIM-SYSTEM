"""OpenVPN certificate integration

Revision ID: 0027_openvpn_cert_integration
Revises: 0027_prefix_system_tables
Create Date: 2026-06-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0027_openvpn_cert_integration"
down_revision = "0027_prefix_system_tables"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name, column_name):
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


def _add_column_if_missing(bind, table_name, column):
    if not _column_exists(bind, table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    _add_column_if_missing(
        bind,
        "openvpn_servers",
        sa.Column("certificate_backend", sa.String(length=32), nullable=False, server_default=sa.text("'metadata'"), comment="证书后端：metadata/local_easyrsa"),
    )
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("easy_rsa_dir", sa.String(length=512), nullable=True, comment="Easy-RSA目录"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("pki_dir", sa.String(length=512), nullable=True, comment="PKI目录"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("ca_cert_path", sa.String(length=512), nullable=True, comment="CA证书路径"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("tls_crypt_key_path", sa.String(length=512), nullable=True, comment="tls-crypt或ta.key路径"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("crl_path", sa.String(length=512), nullable=True, comment="CRL文件路径"))
    _add_column_if_missing(bind, "openvpn_servers", sa.Column("client_config_dir", sa.String(length=512), nullable=True, comment="客户端配置输出目录"))

    _add_column_if_missing(bind, "openvpn_certificates", sa.Column("cert_path", sa.String(length=512), nullable=True, comment="客户端证书路径"))
    _add_column_if_missing(bind, "openvpn_certificates", sa.Column("key_path", sa.String(length=512), nullable=True, comment="客户端私钥路径"))
    _add_column_if_missing(bind, "openvpn_certificates", sa.Column("request_path", sa.String(length=512), nullable=True, comment="证书请求路径"))


def downgrade():
    bind = op.get_bind()
    for column_name in ("request_path", "key_path", "cert_path"):
        if _column_exists(bind, "openvpn_certificates", column_name):
            op.drop_column("openvpn_certificates", column_name)

    for column_name in (
        "client_config_dir",
        "crl_path",
        "tls_crypt_key_path",
        "ca_cert_path",
        "pki_dir",
        "easy_rsa_dir",
        "certificate_backend",
    ):
        if _column_exists(bind, "openvpn_servers", column_name):
            op.drop_column("openvpn_servers", column_name)
