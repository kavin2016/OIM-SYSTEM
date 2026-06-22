"""Add operation logs

Revision ID: 0035_add_operation_logs
Revises: 0034_openvpn_log_pagination
Create Date: 2026-06-22 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import bindparam


revision = "0035_add_operation_logs"
down_revision = "0034_openvpn_log_pagination"
branch_labels = None
depends_on = None


MENU = {
    "name": "操作日志",
    "code": "ops:operation-log:list",
    "path": "/ops/operation-logs",
    "component": "OperationLogManagement",
    "icon": "document",
    "sort_order": 390,
    "description": "操作日志",
}
PERMISSIONS = [
    ("操作日志查询", "ops:operation-log:query", 1, "查询操作日志"),
    ("操作日志详情", "ops:operation-log:detail", 2, "查看操作日志详情"),
    ("操作日志导出", "ops:operation-log:export", 3, "导出操作日志"),
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM sys_permissions WHERE code = :code"), {"code": code}).scalar()


def _table_exists(bind, table_name):
    return bool(bind.execute(sa.text("SHOW TABLES LIKE :table_name"), {"table_name": table_name}).first())


def _index_exists(bind, table_name, index_name):
    return bool(
        bind.execute(
            sa.text(
                """
                SELECT 1
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
                  AND index_name = :index_name
                LIMIT 1
                """
            ),
            {"table_name": table_name, "index_name": index_name},
        ).first()
    )


def _create_index_if_missing(bind, name, table_name, columns):
    if not _index_exists(bind, table_name, name):
        op.create_index(name, table_name, columns)


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
    bind = op.get_bind()
    if not _table_exists(bind, "operation_logs"):
        op.create_table(
            "operation_logs",
            sa.Column("id", sa.Integer(), primary_key=True, index=True, comment="操作日志ID"),
            sa.Column("trace_id", sa.String(length=64), nullable=True, comment="请求追踪ID"),
            sa.Column("operator_id", sa.Integer(), nullable=True, comment="操作人ID"),
            sa.Column("operator_username", sa.String(length=100), nullable=True, comment="操作人账号快照"),
            sa.Column("operator_nickname", sa.String(length=100), nullable=True, comment="操作人昵称快照"),
            sa.Column("department_id", sa.Integer(), nullable=True, comment="操作人部门ID快照"),
            sa.Column("department_name", sa.String(length=100), nullable=True, comment="操作人部门名称快照"),
            sa.Column("module", sa.String(length=64), nullable=False, comment="模块编码"),
            sa.Column("module_name", sa.String(length=100), nullable=False, comment="模块名称"),
            sa.Column("resource_type", sa.String(length=64), nullable=True, comment="资源类型"),
            sa.Column("resource_id", sa.Integer(), nullable=True, comment="资源ID"),
            sa.Column("resource_name", sa.String(length=255), nullable=True, comment="资源名称快照"),
            sa.Column("action", sa.String(length=64), nullable=False, comment="操作动作"),
            sa.Column("action_name", sa.String(length=100), nullable=False, comment="操作名称"),
            sa.Column("method", sa.String(length=16), nullable=True, comment="HTTP方法"),
            sa.Column("path", sa.String(length=255), nullable=True, comment="请求路径"),
            sa.Column("request_params", sa.JSON(), nullable=True, comment="请求URL参数"),
            sa.Column("request_body", sa.JSON(), nullable=True, comment="请求体"),
            sa.Column("response_params", sa.JSON(), nullable=True, comment="返回参数"),
            sa.Column("response_status", sa.Integer(), nullable=True, comment="响应状态码"),
            sa.Column("result", sa.String(length=32), nullable=False, server_default="success", comment="操作结果"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("client_ip", sa.String(length=64), nullable=True, comment="客户端IP"),
            sa.Column("user_agent", sa.String(length=512), nullable=True, comment="客户端信息"),
            sa.Column("duration_ms", sa.Integer(), nullable=True, comment="耗时毫秒"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="操作时间"),
        )
    _create_index_if_missing(bind, "ix_operation_logs_action_id", "operation_logs", ["action", "id"])
    _create_index_if_missing(bind, "ix_operation_logs_created_id", "operation_logs", ["created_at", "id"])
    _create_index_if_missing(bind, "ix_operation_logs_department_id_id", "operation_logs", ["department_id", "id"])
    _create_index_if_missing(bind, "ix_operation_logs_module_id", "operation_logs", ["module", "id"])
    _create_index_if_missing(bind, "ix_operation_logs_operator_id_id", "operation_logs", ["operator_id", "id"])
    _create_index_if_missing(bind, "ix_operation_logs_resource", "operation_logs", ["resource_type", "resource_id"])
    _create_index_if_missing(bind, "ix_operation_logs_result_id", "operation_logs", ["result", "id"])
    _create_index_if_missing(bind, "ix_operation_logs_trace_id", "operation_logs", ["trace_id"])

    ops_id = _permission_id(bind, "ops")
    menu_id = _insert_or_update_permission(
        bind,
        {
            "parent_id": ops_id,
            "name": MENU["name"],
            "code": MENU["code"],
            "type": "menu",
            "path": MENU["path"],
            "component": MENU["component"],
            "icon": MENU["icon"],
            "sort_order": MENU["sort_order"],
            "description": MENU["description"],
            "is_active": True,
            "is_deleted": False,
        },
    )
    _grant_to_existing_roles(bind, menu_id, ["ops", "ops:openvpn:list", "ops:openvpn:server:query"])

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
        _grant_to_existing_roles(bind, permission_id, ["ops", "ops:openvpn:list", "ops:openvpn:server:query"])


def downgrade():
    bind = op.get_bind()
    codes = tuple([MENU["code"], *[item[1] for item in PERMISSIONS]])
    ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM sys_permissions WHERE code IN :codes").bindparams(bindparam("codes", expanding=True)),
            {"codes": codes},
        )
    ]
    if ids:
        bind.execute(
            sa.text("DELETE FROM sys_role_permissions WHERE permission_id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(ids)},
        )
        bind.execute(
            sa.text("DELETE FROM sys_permissions WHERE id IN :ids").bindparams(bindparam("ids", expanding=True)),
            {"ids": tuple(ids)},
        )

    op.drop_index("ix_operation_logs_trace_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_result_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_resource", table_name="operation_logs")
    op.drop_index("ix_operation_logs_operator_id_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_module_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_department_id_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_created_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_action_id", table_name="operation_logs")
    op.drop_table("operation_logs")
