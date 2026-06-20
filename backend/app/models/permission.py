from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True, comment="权限ID")
    parent_id = Column(Integer, ForeignKey("permissions.id", ondelete="SET NULL"), nullable=True, index=True, comment="父级权限ID")
    name = Column(String(100), unique=True, index=True, nullable=False, comment="权限名称")
    code = Column(String(100), unique=True, index=True, nullable=False, comment="权限编码")
    type = Column(String(20), default="button", nullable=False, comment="权限类型：menu=菜单，button=按钮")
    path = Column(String(255), nullable=True, comment="前端路由路径")
    component = Column(String(255), nullable=True, comment="前端组件标识")
    icon = Column(String(64), nullable=True, comment="菜单图标")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序值")
    description = Column(Text, nullable=True, comment="权限描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否正常：0=禁用，1=正常")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除：0=未删除，1=已删除")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    parent = relationship("Permission", remote_side=[id], back_populates="children")
    children = relationship("Permission", back_populates="parent")
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
