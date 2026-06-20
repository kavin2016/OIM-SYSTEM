from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Department(Base):
    __tablename__ = "sys_departments"

    id = Column(Integer, primary_key=True, index=True, comment="部门ID")
    parent_id = Column(Integer, ForeignKey("sys_departments.id", ondelete="SET NULL"), nullable=True, comment="上级部门ID")
    name = Column(String(100), unique=True, index=True, nullable=False, comment="部门名称")
    code = Column(String(64), unique=True, index=True, nullable=False, comment="部门编码")
    description = Column(Text, nullable=True, comment="部门描述")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否正常：0=禁用，1=正常")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除：0=未删除，1=已删除")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    users = relationship("UserDepartment", back_populates="department", cascade="all, delete-orphan")
    parent = relationship("Department", remote_side=[id], back_populates="children")
    children = relationship("Department", back_populates="parent")
