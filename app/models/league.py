"""
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from app.db.base import Base

class League(Base):
    __tablename__ = "leagues"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    entry_fee = Column(Integer, default=0)
    reward_pool = Column(Integer)
    is_active = Column(Boolean, default=False)

"""