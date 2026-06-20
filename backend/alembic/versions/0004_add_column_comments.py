"""Add column comments

Revision ID: 0004_add_column_comments
Revises: 0003_add_audit_fields
Create Date: 2026-06-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0004_add_column_comments"
down_revision = "0003_add_audit_fields"
branch_labels = None
depends_on = None


def _comment(
    table_name,
    column_name,
    existing_type,
    comment,
    nullable=False,
    server_default=None,
    autoincrement=False,
):
    op.alter_column(
        table_name,
        column_name,
        existing_type=existing_type,
        existing_nullable=nullable,
        existing_server_default=server_default,
        autoincrement=autoincrement,
        comment=comment,
    )


def _drop_foreign_keys():
    inspector = inspect(op.get_bind())
    foreign_keys = []
    for table_name in ("user_departments", "user_roles", "role_permissions"):
        for foreign_key in inspector.get_foreign_keys(table_name):
            foreign_keys.append(
                {
                    "name": foreign_key["name"],
                    "source_table": table_name,
                    "local_cols": foreign_key["constrained_columns"],
                    "referent_table": foreign_key["referred_table"],
                    "remote_cols": foreign_key["referred_columns"],
                    "ondelete": foreign_key.get("options", {}).get("ondelete"),
                }
            )
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")
    return foreign_keys


def _restore_foreign_keys(foreign_keys):
    for foreign_key in foreign_keys:
        op.create_foreign_key(
            foreign_key["name"],
            foreign_key["source_table"],
            foreign_key["referent_table"],
            foreign_key["local_cols"],
            foreign_key["remote_cols"],
            ondelete=foreign_key["ondelete"],
        )


def upgrade():
    foreign_keys = _drop_foreign_keys()

    _comment("users", "id", sa.Integer(), "用户ID", autoincrement=True)
    _comment("users", "username", sa.String(length=64), "用户名")
    _comment("users", "email", sa.String(length=128), "邮箱")
    _comment("users", "hashed_password", sa.String(length=256), "加密后的密码")
    _comment("users", "is_active", sa.Boolean(), "是否正常：0=禁用，1=正常", server_default=sa.text("1"))
    _comment("users", "is_admin", sa.Boolean(), "是否管理员：0=否，1=是", server_default=sa.text("0"))
    _comment("users", "created_by", sa.Integer(), "创建人ID", nullable=True)
    _comment("users", "created_at", sa.DateTime(), "创建时间")
    _comment("users", "updated_by", sa.Integer(), "修改人ID", nullable=True)
    _comment("users", "updated_at", sa.DateTime(), "修改时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _comment("departments", "id", sa.Integer(), "部门ID", autoincrement=True)
    _comment("departments", "name", sa.String(length=100), "部门名称")
    _comment("departments", "code", sa.String(length=64), "部门编码")
    _comment("departments", "description", sa.Text(), "部门描述", nullable=True)
    _comment("departments", "is_active", sa.Boolean(), "是否正常：0=禁用，1=正常", server_default=sa.text("1"))
    _comment("departments", "created_by", sa.Integer(), "创建人ID", nullable=True)
    _comment("departments", "created_at", sa.DateTime(), "创建时间", server_default=sa.text("CURRENT_TIMESTAMP"))
    _comment("departments", "updated_by", sa.Integer(), "修改人ID", nullable=True)
    _comment("departments", "updated_at", sa.DateTime(), "修改时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _comment("roles", "id", sa.Integer(), "角色ID", autoincrement=True)
    _comment("roles", "name", sa.String(length=100), "角色名称")
    _comment("roles", "code", sa.String(length=64), "角色编码")
    _comment("roles", "description", sa.Text(), "角色描述", nullable=True)
    _comment("roles", "is_active", sa.Boolean(), "是否正常：0=禁用，1=正常", server_default=sa.text("1"))
    _comment("roles", "created_by", sa.Integer(), "创建人ID", nullable=True)
    _comment("roles", "created_at", sa.DateTime(), "创建时间", server_default=sa.text("CURRENT_TIMESTAMP"))
    _comment("roles", "updated_by", sa.Integer(), "修改人ID", nullable=True)
    _comment("roles", "updated_at", sa.DateTime(), "修改时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _comment("permissions", "id", sa.Integer(), "权限ID", autoincrement=True)
    _comment("permissions", "name", sa.String(length=100), "权限名称")
    _comment("permissions", "code", sa.String(length=100), "权限编码")
    _comment("permissions", "description", sa.Text(), "权限描述", nullable=True)
    _comment("permissions", "is_active", sa.Boolean(), "是否正常：0=禁用，1=正常", server_default=sa.text("1"))
    _comment("permissions", "created_by", sa.Integer(), "创建人ID", nullable=True)
    _comment("permissions", "created_at", sa.DateTime(), "创建时间", server_default=sa.text("CURRENT_TIMESTAMP"))
    _comment("permissions", "updated_by", sa.Integer(), "修改人ID", nullable=True)
    _comment("permissions", "updated_at", sa.DateTime(), "修改时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _comment("user_departments", "id", sa.Integer(), "用户部门关系ID", autoincrement=True)
    _comment("user_departments", "user_id", sa.Integer(), "用户ID")
    _comment("user_departments", "department_id", sa.Integer(), "部门ID")
    _comment("user_departments", "is_primary", sa.Boolean(), "是否主部门：0=否，1=是", server_default=sa.text("0"))
    _comment("user_departments", "created_at", sa.DateTime(), "创建时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _comment("user_roles", "id", sa.Integer(), "用户角色关系ID", autoincrement=True)
    _comment("user_roles", "user_id", sa.Integer(), "用户ID")
    _comment("user_roles", "role_id", sa.Integer(), "角色ID")
    _comment("user_roles", "created_at", sa.DateTime(), "创建时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _comment("role_permissions", "id", sa.Integer(), "角色权限关系ID", autoincrement=True)
    _comment("role_permissions", "role_id", sa.Integer(), "角色ID")
    _comment("role_permissions", "permission_id", sa.Integer(), "权限ID")
    _comment("role_permissions", "created_at", sa.DateTime(), "创建时间", server_default=sa.text("CURRENT_TIMESTAMP"))

    _restore_foreign_keys(foreign_keys)


def downgrade():
    for table_name, column_names in {
        "users": (
            "id",
            "username",
            "email",
            "hashed_password",
            "is_active",
            "is_admin",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        ),
        "departments": (
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        ),
        "roles": (
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        ),
        "permissions": (
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "created_by",
            "created_at",
            "updated_by",
            "updated_at",
        ),
        "user_departments": ("id", "user_id", "department_id", "is_primary", "created_at"),
        "user_roles": ("id", "user_id", "role_id", "created_at"),
        "role_permissions": ("id", "role_id", "permission_id", "created_at"),
    }.items():
        for column_name in column_names:
            op.alter_column(table_name, column_name, comment=None)
