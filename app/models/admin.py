"""
from sqlalchemy import Column, Integer, String
from app.db.base import Base

class AdminSetting(Base):
    __tablename__ = "admin_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(String)
"""