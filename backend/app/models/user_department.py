from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class UserDepartment(Base):
    __tablename__ = "sys_user_departments"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_departments_user"),
        UniqueConstraint("user_id", "department_id", name="uq_user_departments_user_department"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="用户部门关系ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    department_id = Column(Integer, ForeignKey("sys_departments.id", ondelete="CASCADE"), nullable=False, comment="部门ID")
    is_primary = Column(Boolean, default=False, nullable=False, comment="是否主部门：0=否，1=是")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    user = relationship("User", back_populates="departments")
    department = relationship("Department", back_populates="users")
