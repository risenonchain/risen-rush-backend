from sqlalchemy import Column, Integer, ForeignKey
from app.db.database import Base


class PointWallet(Base):
    __tablename__ = "point_wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    total_points_earned = Column(Integer, default=0, nullable=False)
    available_points = Column(Integer, default=0, nullable=False)
    claimed_points = Column(Integer, default=0, nullable=False)