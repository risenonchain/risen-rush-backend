from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base


class PointWallet(Base):
    __tablename__ = "point_wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    total_points_earned = Column(Integer, default=0, nullable=False)
    available_points = Column(Integer, default=0, nullable=False)
    claimed_points = Column(Integer, default=0, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")