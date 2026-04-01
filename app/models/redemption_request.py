from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.database import Base


class RedemptionRequest(Base):
    __tablename__ = "redemption_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    username_snapshot = Column(String, nullable=False)
    email_snapshot = Column(String, nullable=False)
    wallet_address_snapshot = Column(String, nullable=False)

    points_requested = Column(Integer, nullable=False)
    status = Column(String, default="pending", nullable=False, index=True)

    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)