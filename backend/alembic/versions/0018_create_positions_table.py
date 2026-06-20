"""Create positions table

Revision ID: 0018_create_positions
Revises: 0017_nullable_user_email
Create Date: 2026-06-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0018_create_positions"
down_revision = "0017_nullable_user_email"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False, comment="岗位ID"),
        sa.Column("code", sa.String(length=64), nullable=False, comment="岗位编码"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="岗位名称"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0", comment="显示顺序"),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0", comment="状态：0=正常，1=停用"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否删除：0=未删除，1=已删除"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建者"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="更新者"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.UniqueConstraint("code", name="uq_positions_code"),
        sa.UniqueConstraint("name", name="uq_positions_name"),
    )
    op.create_index("ix_positions_id", "positions", ["id"])
    op.create_index("ix_positions_code", "positions", ["code"])
    op.create_index("ix_positions_name", "positions", ["name"])
    op.create_index("ix_positions_status", "positions", ["status"])
    op.create_index("ix_positions_is_deleted", "positions", ["is_deleted"])
    op.create_index("ix_positions_sort_order", "positions", ["sort_order"])


def downgrade():
    op.drop_index("ix_positions_sort_order", table_name="positions")
    op.drop_index("ix_positions_is_deleted", table_name="positions")
    op.drop_index("ix_positions_status", table_name="positions")
    op.drop_index("ix_positions_name", table_name="positions")
    op.drop_index("ix_positions_code", table_name="positions")
    op.drop_index("ix_positions_id", table_name="positions")
    op.drop_table("positions")
