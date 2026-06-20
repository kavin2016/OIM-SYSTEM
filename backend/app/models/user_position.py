from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from ..database import Base


class UserPosition(Base):
    __tablename__ = "sys_user_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "position_id", name="uq_user_positions_user_position"),
    )

    id = Column(Integer, primary_key=True, index=True, comment="用户岗位关系ID")
    user_id = Column(Integer, ForeignKey("sys_users.id", ondelete="CASCADE"), nullable=False, comment="用户ID")
    position_id = Column(Integer, ForeignKey("sys_positions.id", ondelete="CASCADE"), nullable=False, comment="岗位ID")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")

    user = relationship("User", back_populates="positions")
    position = relationship("Position", back_populates="users")
