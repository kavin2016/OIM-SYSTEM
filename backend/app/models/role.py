from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Role(Base):
    __tablename__ = "sys_roles"

    id = Column(Integer, primary_key=True, index=True, comment="角色ID")
    name = Column(String(100), unique=True, index=True, nullable=False, comment="角色名称")
    code = Column(String(64), unique=True, index=True, nullable=False, comment="角色编码")
    sort_order = Column(Integer, default=0, nullable=False, comment="角色顺序")
    description = Column(Text, nullable=True, comment="角色描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否正常：0=禁用，1=正常")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除：0=未删除，1=已删除")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    users = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
