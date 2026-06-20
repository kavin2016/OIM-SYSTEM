"""Rename system menu labels

Revision ID: 0010_rename_system_menu_labels
Revises: 0009_add_user_profile_fields
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_rename_system_menu_labels"
down_revision = "0009_add_user_profile_fields"
branch_labels = None
depends_on = None

UPDATES = {
    "system:settings": ("系统管理", "系统管理一级菜单"),
    "system:user:list": ("用户管理", "用户管理二级菜单"),
    "system:department:list": ("部门管理", "部门管理二级菜单"),
    "system:role:list": ("角色管理", "角色管理二级菜单"),
}

DOWNDATES = {
    "system:settings": ("系统设置", "系统设置一级菜单"),
    "system:user:list": ("用户列表", "用户列表二级菜单"),
    "system:department:list": ("部门列表", "部门列表二级菜单"),
    "system:role:list": ("角色列表", "角色列表二级菜单"),
}


def apply_updates(values):
    bind = op.get_bind()
    for code, (name, description) in values.items():
        bind.execute(
            sa.text("UPDATE permissions SET name = :name, description = :description WHERE code = :code"),
            {"name": name, "description": description, "code": code},
        )


def upgrade():
    apply_updates(UPDATES)


def downgrade():
    apply_updates(DOWNDATES)
