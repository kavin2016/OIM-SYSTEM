from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class UserRole(Base):
    __tablename__ = "sys_user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_roles_user"),
        UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="用户角色关系ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    role_id = Column(Integer, ForeignKey("sys_roles.id", ondelete="CASCADE"), nullable=False, comment="角色ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    user = relationship("User", back_populates="roles")
    role = relationship("Role", back_populates="users")
