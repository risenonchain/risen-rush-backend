from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, BigInteger
from app.db.database import Base

class BridgeTransaction(Base):
    __tablename__ = "bridge_transactions"

    id = Column(Integer, primary_key=True, index=True)

    user_address = Column(String, index=True, nullable=False)
    token_address = Column(String, nullable=False)
    amount = Column(BigInteger, nullable=False)

    source_chain_id = Column(Integer, nullable=False)
    dest_chain_id = Column(Integer, nullable=False)

    source_tx_hash = Column(String, unique=True, index=True, nullable=False)
    nonce = Column(BigInteger, nullable=False)

    signature = Column(String, nullable=True)
    is_claimed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
