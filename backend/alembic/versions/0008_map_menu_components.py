"""Map menu permissions to dedicated frontend components

Revision ID: 0008_map_menu_components
Revises: 0007_add_permission_icons
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_map_menu_components"
down_revision = "0007_add_permission_icons"
branch_labels = None
depends_on = None

COMPONENT_MAP = {
    "system:user:list": "UserList",
    "system:department:list": "DepartmentList",
    "system:role:list": "RoleList",
}


def upgrade():
    bind = op.get_bind()
    for code, component in COMPONENT_MAP.items():
        bind.execute(
            sa.text("UPDATE permissions SET component = :component WHERE code = :code"),
            {"component": component, "code": code},
        )


def downgrade():
    bind = op.get_bind()
    for code in COMPONENT_MAP:
        bind.execute(
            sa.text("UPDATE permissions SET component = 'AdminPanel' WHERE code = :code"),
            {"code": code},
        )

