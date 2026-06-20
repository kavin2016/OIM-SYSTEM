from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, String, Text

from ..database import Base


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True, comment="域名ID")
    code = Column(String(255), unique=True, index=True, nullable=False, comment="域名地址")
    name = Column(String(100), unique=True, index=True, nullable=False, comment="域名名称")
    registrar = Column(String(100), nullable=True, comment="注册商")
    expiry_date = Column(Date, nullable=True, comment="到期日期")
    sort_order = Column(Integer, default=0, nullable=False, comment="显示顺序")
    status = Column(Integer, default=0, nullable=False, comment="状态：0=正常，1=停用")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否删除：0=未删除，1=已删除")
    created_by = Column(Integer, nullable=True, comment="创建者")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_by = Column(Integer, nullable=True, comment="更新者")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    remark = Column(Text, nullable=True, comment="备注")
