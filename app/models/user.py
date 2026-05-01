from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    reset_token = Column(String, unique=True, index=True, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)

    # --- New profile / referral / admin fields ---
    referral_code = Column(String, unique=True, index=True, nullable=True)
    referred_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    wallet_address = Column(String, nullable=True)

    avatar_url = Column(String, nullable=True)
    generated_avatar_url = Column(String, nullable=True)

    vault_trials = Column(Integer, default=0, nullable=False)

    # Monetization
    is_premium = Column(Boolean, default=False, nullable=False)
    premium_expires_at = Column(DateTime, nullable=True)

    # Gaming
    best_score = Column(Integer, default=0, nullable=False)
    best_level = Column(Integer, default=1, nullable=False)

    # Ad Tracking
    ads_watched_today = Column(Integer, default=0, nullable=False)
    last_ad_date = Column(DateTime, nullable=True)

    is_admin = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)