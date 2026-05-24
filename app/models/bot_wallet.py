from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.database import Base

class GuardianBotWallet(Base):
    __tablename__ = "guardian_bot_wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, index=True, nullable=False)

    address = Column(String, unique=True, index=True, nullable=False)
    encrypted_private_key = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
