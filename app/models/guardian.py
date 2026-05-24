from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.database import Base

class GuardianContractScan(Base):
    __tablename__ = "guardian_contract_scans"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True, nullable=False)
    network = Column(String, default="bsc")

    # Analysis results
    risk_score = Column(Integer)  # 0-100 (higher is riskier)
    is_honeypot = Column(Boolean, default=False)
    buy_tax = Column(Float, default=0.0)
    sell_tax = Column(Float, default=0.0)

    # Ownership & Liquidity
    owner_address = Column(String, nullable=True)
    is_proxy = Column(Boolean, default=False)
    has_mint_function = Column(Boolean, default=False)
    is_open_source = Column(Boolean, default=True)

    # Raw Data storage
    raw_data = Column(JSON, nullable=True)

    # User Context
    scanned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

class GuardianWatchlist(Base):
    __tablename__ = "guardian_watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    target_address = Column(String, nullable=False)
    target_type = Column(String)  # 'contract' or 'wallet'
    label = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class GuardianAlert(Base):
    __tablename__ = "guardian_alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)

    severity = Column(String)  # 'low', 'medium', 'high', 'critical'
    category = Column(String)  # 'contract_risk', 'wallet_activity', 'system'

    title = Column(String, nullable=False)
    message = Column(String, nullable=False)

    related_address = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
