"""Split OpenVPN management menus

Revision ID: 0028_split_openvpn_menus
Revises: 0027_openvpn_cert_integration
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import bindparam


revision = "0028_split_openvpn_menus"
down_revision = "0027_openvpn_cert_integration"
branch_labels = None
depends_on = None


OPENVPN_MENUS = [
    {
        "name": "OpenVPN服务器管理",
        "code": "ops:openvpn:server:list",
        "path": "/ops/openvpn/servers",
        "component": "OpenVpnServerManagement",
        "icon": "connection",
        "sort_order": 301,
        "query_code": "ops:openvpn:server:query",
        "children": [
            "ops:openvpn:server:query",
            "ops:openvpn:server:create",
            "ops:openvpn:server:update",
            "ops:openvpn:server:delete",
            "ops:openvpn:server:test",
            "ops:openvpn:server:set-default",
        ],
    },
    {
        "name": "OpenVPN用户管理",
        "code": "ops:openvpn:account:list",
        "path": "/ops/openvpn/accounts",
        "component": "OpenVpnAccountManagement",
        "icon": "users",
        "sort_order": 302,
        "query_code": "ops:openvpn:account:query",
        "children": [
            "ops:openvpn:account:query",
            "ops:openvpn:account:enable",
            "ops:openvpn:account:disable",
            "ops:openvpn:account:assign-server",
            "ops:openvpn:account:download-config",
            "ops:openvpn:cert:query",
            "ops:openvpn:cert:issue",
            "ops:openvpn:cert:revoke",
            "ops:openvpn:cert:renew",
        ],
    },
    {
        "name": "OpenVPN在线会话",
        "code": "ops:openvpn:session:list",
        "path": "/ops/openvpn/sessions",
        "component": "OpenVpnSessionManagement",
        "icon": "monitor",
        "sort_order": 303,
        "query_code": "ops:openvpn:session:query",
        "children": [
            "ops:openvpn:session:query",
            "ops:openvpn:session:kick",
        ],
    },
    {
        "name": "OpenVPN连接日志",
        "code": "ops:openvpn:log:list",
        "path": "/ops/openvpn/logs",
        "component": "OpenVpnLogManagement",
        "icon": "document",
        "sort_order": 304,
        "query_code": "ops:openvpn:log:query",
        "children": [
            "ops:openvpn:log:query",
            "ops:openvpn:log:export",
        ],
    },
    {
        "name": "OpenVPN分配策略",
        "code": "ops:openvpn:rule:list",
        "path": "/ops/openvpn/rules",
        "component": "OpenVpnRuleManagement",
        "icon": "setting",
        "sort_order": 305,
        "query_code": "ops:openvpn:rule:query",
        "children": [
            "ops:openvpn:rule:query",
            "ops:openvpn:rule:create",
            "ops:openvpn:rule:update",
            "ops:openvpn:rule:delete",
        ],
    },
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM sys_permissions WHERE code = :code"), {"code": code}).scalar()


def _insert_or_update_menu(bind, parent_id, item):
    permission_id = _permission_id(bind, item["code"])
    values = {
        "parent_id": parent_id,
        "name": item["name"],
        "code": item["code"],
        "type": "menu",
        "path": item["path"],
        "component": item["component"],
        "icon": item["icon"],
        "sort_order": item["sort_order"],
        "description": item["name"],
        "is_active": True,
        "is_deleted": False,
    }
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


def _grant_menu_to_existing_roles(bind, menu_id, query_code):
    query_permission_id = _permission_id(bind, query_code)
    old_menu_id = _permission_id(bind, "ops:openvpn:list")
    source_ids = [item for item in (query_permission_id, old_menu_id) if item]
    if not source_ids:
        return
    statement = sa.text(
            """
            INSERT INTO sys_role_permissions (role_id, permission_id, created_at)
            SELECT DISTINCT rp.role_id, :menu_id, CURRENT_TIMESTAMP
            FROM sys_role_permissions rp
            WHERE rp.permission_id IN :source_ids
              AND NOT EXISTS (
                SELECT 1
                FROM sys_role_permissions existing
                WHERE existing.role_id = rp.role_id
                  AND existing.permission_id = :menu_id
              )
            """
    ).bindparams(bindparam("source_ids", expanding=True))
    bind.execute(
        statement,
        {"menu_id": menu_id, "source_ids": tuple(source_ids)},
    )


def upgrade():
    bind = op.get_bind()
    ops_id = _permission_id(bind, "ops")
    old_menu_id = _permission_id(bind, "ops:openvpn:list")

    for item in OPENVPN_MENUS:
        menu_id = _insert_or_update_menu(bind, ops_id, item)
        for child_code in item["children"]:
            bind.execute(
                sa.text("UPDATE sys_permissions SET parent_id = :parent_id WHERE code = :code"),
                {"parent_id": menu_id, "code": child_code},
            )
        _grant_menu_to_existing_roles(bind, menu_id, item["query_code"])

    if old_menu_id:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
                SET is_active = 0,
                    path = NULL,
                    component = NULL
                WHERE id = :id
                """
            ),
            {"id": old_menu_id},
        )


def downgrade():
    bind = op.get_bind()
    old_menu_id = _permission_id(bind, "ops:openvpn:list")
    if old_menu_id:
        bind.execute(
            sa.text(
                """
                UPDATE sys_permissions
                SET parent_id = :parent_id,
                    name = 'OpenVPN管理',
                    type = 'menu',
                    path = '/ops/openvpn',
                    component = 'OpenVpnManagement',
                    icon = 'connection',
                    sort_order = 301,
                    is_active = 1,
                    is_deleted = 0
                WHERE id = :id
                """
            ),
            {"parent_id": _permission_id(bind, "ops"), "id": old_menu_id},
        )
        for item in OPENVPN_MENUS:
            for child_code in item["children"]:
                bind.execute(
                    sa.text("UPDATE sys_permissions SET parent_id = :parent_id WHERE code = :code"),
                    {"parent_id": old_menu_id, "code": child_code},
                )

    menu_codes = tuple(item["code"] for item in OPENVPN_MENUS)
    menu_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM sys_permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
            {"codes": menu_codes},
        )
    ]
    if menu_ids:
        bind.execute(
            sa.text("DELETE FROM sys_role_permissions WHERE permission_id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(menu_ids)},
        )
        bind.execute(
            sa.text("DELETE FROM sys_permissions WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(menu_ids)},
        )
