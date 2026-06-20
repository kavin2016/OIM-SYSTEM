"""Add icons for menu and button permissions

Revision ID: 0007_add_permission_icons
Revises: 0006_extend_permissions
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_add_permission_icons"
down_revision = "0006_extend_permissions"
branch_labels = None
depends_on = None

ICON_MAP = {
    "system:settings": "settings",
    "system:user:list": "users",
    "system:user:query": "search",
    "system:user:create": "plus",
    "system:user:update": "edit",
    "system:user:delete": "trash",
    "system:department:list": "building",
    "system:department:query": "search",
    "system:department:create": "plus",
    "system:department:update": "edit",
    "system:department:delete": "trash",
    "system:role:list": "shield",
    "system:role:query": "search",
    "system:role:create": "plus",
    "system:role:update": "edit",
    "system:role:delete": "trash",
}


def upgrade():
    bind = op.get_bind()
    for code, icon in ICON_MAP.items():
        bind.execute(
            sa.text("UPDATE permissions SET icon = :icon WHERE code = :code"),
            {"icon": icon, "code": code},
        )


def downgrade():
    bind = op.get_bind()
    button_codes = [code for code in ICON_MAP if not code.endswith(":list") and code != "system:settings"]
    for code in button_codes:
        bind.execute(
            sa.text("UPDATE permissions SET icon = NULL WHERE code = :code"),
            {"code": code},
        )

