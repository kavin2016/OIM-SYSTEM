from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text

from ..database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"
    __table_args__ = (
        Index("ix_operation_logs_operator_id_id", "operator_id", "id"),
        Index("ix_operation_logs_department_id_id", "department_id", "id"),
        Index("ix_operation_logs_module_id", "module", "id"),
        Index("ix_operation_logs_resource", "resource_type", "resource_id"),
        Index("ix_operation_logs_action_id", "action", "id"),
        Index("ix_operation_logs_result_id", "result", "id"),
        Index("ix_operation_logs_created_id", "created_at", "id"),
        Index("ix_operation_logs_trace_id", "trace_id"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="操作日志ID")
    trace_id = Column(String(64), nullable=True, comment="请求追踪ID")
    operator_id = Column(Integer, nullable=True, comment="操作人ID")
    operator_username = Column(String(100), nullable=True, comment="操作人账号快照")
    operator_nickname = Column(String(100), nullable=True, comment="操作人昵称快照")
    department_id = Column(Integer, nullable=True, comment="操作人部门ID快照")
    department_name = Column(String(100), nullable=True, comment="操作人部门名称快照")
    module = Column(String(64), nullable=False, comment="模块编码")
    module_name = Column(String(100), nullable=False, comment="模块名称")
    resource_type = Column(String(64), nullable=True, comment="资源类型")
    resource_id = Column(Integer, nullable=True, comment="资源ID")
    resource_name = Column(String(255), nullable=True, comment="资源名称快照")
    action = Column(String(64), nullable=False, comment="操作动作")
    action_name = Column(String(100), nullable=False, comment="操作名称")
    method = Column(String(16), nullable=True, comment="HTTP方法")
    path = Column(String(255), nullable=True, comment="请求路径")
    request_params = Column(JSON, nullable=True, comment="请求URL参数")
    request_body = Column(JSON, nullable=True, comment="请求体")
    response_params = Column(JSON, nullable=True, comment="返回参数")
    response_status = Column(Integer, nullable=True, comment="响应状态码")
    result = Column(String(32), default="success", nullable=False, comment="操作结果")
    error_message = Column(Text, nullable=True, comment="错误信息")
    client_ip = Column(String(64), nullable=True, comment="客户端IP")
    user_agent = Column(String(512), nullable=True, comment="客户端信息")
    duration_ms = Column(Integer, nullable=True, comment="耗时毫秒")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="操作时间")
