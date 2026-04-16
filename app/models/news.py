from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from app.db.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    summary = Column(String(300), nullable=False)
    details = Column(Text, nullable=False)
    url = Column(String(300), nullable=True)  # Optional: for external links
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
