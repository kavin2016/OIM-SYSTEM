from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text

from ..database import Base


class LoginLog(Base):
    __tablename__ = "login_logs"
    __table_args__ = (
        Index("ix_login_logs_user_id_id", "user_id", "id"),
        Index("ix_login_logs_username_id", "username", "id"),
        Index("ix_login_logs_department_id_id", "department_id", "id"),
        Index("ix_login_logs_result_id", "result", "id"),
        Index("ix_login_logs_created_id", "created_at", "id"),
        Index("ix_login_logs_trace_id", "trace_id"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="登录日志ID")
    trace_id = Column(String(64), nullable=True, comment="请求追踪ID")
    user_id = Column(Integer, nullable=True, comment="用户ID")
    username = Column(String(100), nullable=True, comment="登录账号")
    nickname = Column(String(100), nullable=True, comment="用户昵称快照")
    department_id = Column(Integer, nullable=True, comment="用户部门ID快照")
    department_name = Column(String(100), nullable=True, comment="用户部门名称快照")
    login_type = Column(String(32), default="password", nullable=False, comment="登录类型")
    method = Column(String(16), nullable=True, comment="HTTP方法")
    path = Column(String(255), nullable=True, comment="请求路径")
    request_params = Column(JSON, nullable=True, comment="请求URL参数")
    request_body = Column(JSON, nullable=True, comment="请求体")
    response_params = Column(JSON, nullable=True, comment="返回参数")
    response_status = Column(Integer, nullable=True, comment="响应状态码")
    result = Column(String(32), default="success", nullable=False, comment="登录结果")
    error_message = Column(Text, nullable=True, comment="错误信息")
    client_ip = Column(String(64), nullable=True, comment="客户端IP")
    user_agent = Column(String(512), nullable=True, comment="客户端信息")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="登录时间")
