from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class UserDataScopeDepartment(Base):
    __tablename__ = "sys_user_data_scope_departments"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_data_scope_departments_user"),
        UniqueConstraint("user_id", "department_id", name="uq_user_data_scope_departments_user_department"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="用户数据范围部门关系ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, index=True, comment="用户ID")
    department_id = Column(Integer, ForeignKey("sys_departments.id", ondelete="CASCADE"), nullable=False, index=True, comment="部门ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    user = relationship("User", back_populates="data_scope_departments")
    department = relationship("Department")
