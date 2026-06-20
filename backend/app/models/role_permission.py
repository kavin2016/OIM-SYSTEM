from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class RolePermission(Base):
    __tablename__ = "sys_role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="角色权限关系ID")
    role_id = Column(Integer, ForeignKey("sys_roles.id", ondelete="CASCADE"), nullable=False, comment="角色ID")
    permission_id = Column(Integer, ForeignKey("sys_permissions.id", ondelete="CASCADE"), nullable=False, comment="权限ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")
