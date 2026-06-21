"""Optimize OpenVPN log pagination indexes

Revision ID: 0034_openvpn_log_pagination
Revises: 0033_openvpn_traffic_monitoring
Create Date: 2026-06-21 00:00:00.000000
"""

from alembic import op


revision = "0034_openvpn_log_pagination"
down_revision = "0033_openvpn_traffic_monitoring"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_openvpn_logs_server_id_id", "openvpn_connection_logs", ["server_id", "id"])
    op.create_index("ix_openvpn_logs_user_id_id", "openvpn_connection_logs", ["user_id", "id"])
    op.create_index("ix_openvpn_logs_action_id", "openvpn_connection_logs", ["action", "id"])
    op.create_index("ix_openvpn_logs_occurred_id", "openvpn_connection_logs", ["occurred_at", "id"])


def downgrade():
    op.drop_index("ix_openvpn_logs_occurred_id", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_action_id", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_user_id_id", table_name="openvpn_connection_logs")
    op.drop_index("ix_openvpn_logs_server_id_id", table_name="openvpn_connection_logs")
