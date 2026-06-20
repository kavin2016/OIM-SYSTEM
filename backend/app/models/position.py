from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class Position(Base):
    __tablename__ = "sys_positions"

    id = Column(Integer, primary_key=True, index=True, comment="岗位ID")
    code = Column(String(64), unique=True, index=True, nullable=False, comment="岗位编码")
    name = Column(String(100), unique=True, index=True, nullable=False, comment="岗位名称")
    sort_order = Column(Integer, default=0, nullable=False, comment="显示顺序")
    status = Column(Integer, default=0, nullable=False, comment="状态：0=正常，1=停用")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除：0=未删除，1=已删除")
    created_by = Column(Integer, nullable=True, comment="创建者")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="更新者")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    remark = Column(Text, nullable=True, comment="备注")

    users = relationship("UserPosition", back_populates="position", cascade="all, delete-orphan")
