"""Use dedicated OpenVPN frontend components

Revision ID: 0029_openvpn_split_components
Revises: 0028_split_openvpn_menus
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0029_openvpn_split_components"
down_revision = "0028_split_openvpn_menus"
branch_labels = None
depends_on = None


COMPONENT_MAP = {
    "ops:openvpn:server:list": "OpenVpnServerManagement",
    "ops:openvpn:account:list": "OpenVpnAccountManagement",
    "ops:openvpn:session:list": "OpenVpnSessionManagement",
    "ops:openvpn:log:list": "OpenVpnLogManagement",
    "ops:openvpn:rule:list": "OpenVpnRuleManagement",
}


def upgrade():
    bind = op.get_bind()
    for code, component in COMPONENT_MAP.items():
        bind.execute(
            sa.text("UPDATE sys_permissions SET component = :component WHERE code = :code"),
            {"code": code, "component": component},
        )


def downgrade():
    bind = op.get_bind()
    for code in COMPONENT_MAP:
        bind.execute(
            sa.text("UPDATE sys_permissions SET component = 'OpenVpnManagement' WHERE code = :code"),
            {"code": code},
        )
