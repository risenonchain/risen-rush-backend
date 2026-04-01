from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.db.database import Base


class ReferralReward(Base):
    __tablename__ = "referral_rewards"

    id = Column(Integer, primary_key=True, index=True)

    referrer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    referred_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    reward_type = Column(String, default="vault_trial", nullable=False)
    reward_value = Column(Integer, default=1, nullable=False)

    status = Column(String, default="granted", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)