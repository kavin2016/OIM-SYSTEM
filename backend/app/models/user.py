from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class User(Base):
    __tablename__ = "sys_users"

    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(64), unique=True, index=True, nullable=False, comment="用户名")
    nickname = Column(String(64), nullable=True, comment="昵称")
    gender = Column(String(16), nullable=True, comment="性别")
    phone = Column(String(32), nullable=True, comment="手机号")
    position = Column(String(64), nullable=True, comment="岗位")
    remark = Column(Text, nullable=True, comment="备注")
    contacts = Column(JSON, nullable=True, comment="联系方式列表")
    email = Column(String(128), unique=True, index=True, nullable=True, comment="邮箱")
    hashed_password = Column(String(256), nullable=False, comment="加密后的密码")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否正常：0=禁用，1=正常")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除：0=未删除，1=已删除")
    is_admin = Column(Boolean, default=False, nullable=False, comment="是否管理员：0=否，1=是")
    created_by = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="修改人ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="修改时间")

    departments = relationship("UserDepartment", back_populates="user", cascade="all, delete-orphan")
    data_scope_departments = relationship("UserDataScopeDepartment", back_populates="user", cascade="all, delete-orphan")
    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    positions = relationship("UserPosition", back_populates="user", cascade="all, delete-orphan")
