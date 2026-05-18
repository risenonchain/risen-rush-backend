from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Boolean
from app.db.database import Base

class Season(Base):
    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
