"""Add domain management

Revision ID: 0024_domain_management
Revises: 0023_drop_rest_rule_legacy_cols
Create Date: 2026-06-13 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_domain_management"
down_revision = "0023_drop_rest_rule_legacy_cols"
branch_labels = None
depends_on = None

DOMAIN_PERMISSIONS = [
    {
        "name": "域名管理",
        "code": "system:domain:list",
        "type": "menu",
        "path": "/admin/domains",
        "component": "DomainList",
        "icon": "link",
        "sort_order": 105,
        "description": "域名管理二级菜单",
        "children": [
            ("域名查询", "system:domain:query", "查询域名列表"),
            ("域名新增", "system:domain:create", "新增域名"),
            ("域名修改", "system:domain:update", "修改域名"),
            ("域名删除", "system:domain:delete", "删除域名"),
        ],
    }
]


def _permission_id(bind, code):
    return bind.execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}).scalar()


def _upsert_permission(bind, item, parent_id=None):
    existing_id = _permission_id(bind, item["code"])
    values = {
        "parent_id": parent_id,
        "name": item["name"],
        "code": item["code"],
        "type": item["type"],
        "path": item.get("path"),
        "component": item.get("component"),
        "icon": item.get("icon"),
        "sort_order": item["sort_order"],
        "description": item.get("description"),
        "is_active": True,
        "is_deleted": False,
    }
    if existing_id:
        bind.execute(
            sa.text(
                """
                UPDATE permissions
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
            {**values, "id": existing_id},
        )
        permission_id = existing_id
    else:
        result = bind.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (parent_id, name, code, type, path, component, icon, sort_order, description, is_active, is_deleted)
                VALUES
                    (:parent_id, :name, :code, :type, :path, :component, :icon, :sort_order, :description, :is_active, :is_deleted)
                """
            ),
            values,
        )
        permission_id = result.lastrowid

    for index, child in enumerate(item.get("children", []), start=1):
        child_item = {
            "name": child[0],
            "code": child[1],
            "type": "button",
            "path": None,
            "component": None,
            "icon": None,
            "sort_order": item["sort_order"] * 10 + index,
            "description": child[2],
        }
        _upsert_permission(bind, child_item, permission_id)

    return permission_id


def _grant_to_admin_role(bind, codes):
    admin_role_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = :code AND is_deleted = 0"),
        {"code": "admin"},
    ).scalar()
    if not admin_role_id:
        return
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM permissions WHERE code IN :codes"),
            {"codes": tuple(codes)},
        )
    ]
    for permission_id in permission_ids:
        exists = bind.execute(
            sa.text(
                """
                SELECT id FROM role_permissions
                WHERE role_id = :role_id AND permission_id = :permission_id
                """
            ),
            {"role_id": admin_role_id, "permission_id": permission_id},
        ).scalar()
        if not exists:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id, created_at)
                    VALUES (:role_id, :permission_id, CURRENT_TIMESTAMP)
                    """
                ),
                {"role_id": admin_role_id, "permission_id": permission_id},
            )


def upgrade():
    op.create_table(
        "domains",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="域名ID"),
        sa.Column("code", sa.String(length=255), nullable=False, comment="域名地址"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="域名名称"),
        sa.Column("registrar", sa.String(length=100), nullable=True, comment="注册商"),
        sa.Column("expiry_date", sa.Date(), nullable=True, comment="到期日期"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="显示顺序"),
        sa.Column("status", sa.Integer(), nullable=False, server_default=sa.text("0"), comment="状态：0=正常，1=停用"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否删除：0=未删除，1=已删除"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建者"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="更新者"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.UniqueConstraint("code", name="uq_domains_code"),
        sa.UniqueConstraint("name", name="uq_domains_name"),
    )
    op.create_index("ix_domains_id", "domains", ["id"])
    op.create_index("ix_domains_code", "domains", ["code"])
    op.create_index("ix_domains_name", "domains", ["name"])
    op.create_index("ix_domains_status", "domains", ["status"])
    op.create_index("ix_domains_is_deleted", "domains", ["is_deleted"])
    op.create_index("ix_domains_sort_order", "domains", ["sort_order"])
    op.create_index("ix_domains_expiry_date", "domains", ["expiry_date"])

    bind = op.get_bind()
    system_parent_id = _permission_id(bind, "system:settings")
    all_codes = []
    for permission in DOMAIN_PERMISSIONS:
        _upsert_permission(bind, permission, system_parent_id)
        all_codes.append(permission["code"])
        all_codes.extend(child[1] for child in permission["children"])
    _grant_to_admin_role(bind, all_codes)


def downgrade():
    bind = op.get_bind()
    codes = ["system:domain:list", "system:domain:query", "system:domain:create", "system:domain:update", "system:domain:delete"]
    permission_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT id FROM permissions WHERE code IN :codes"),
            {"codes": tuple(codes)},
        )
    ]
    if permission_ids:
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id IN :permission_ids"),
            {"permission_ids": tuple(permission_ids)},
        )
    bind.execute(sa.text("DELETE FROM permissions WHERE code IN :codes"), {"codes": tuple(codes)})

    op.drop_index("ix_domains_expiry_date", table_name="domains")
    op.drop_index("ix_domains_sort_order", table_name="domains")
    op.drop_index("ix_domains_is_deleted", table_name="domains")
    op.drop_index("ix_domains_status", table_name="domains")
    op.drop_index("ix_domains_name", table_name="domains")
    op.drop_index("ix_domains_code", table_name="domains")
    op.drop_index("ix_domains_id", table_name="domains")
    op.drop_table("domains")
