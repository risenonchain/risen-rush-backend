from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base


class DailyTrial(Base):
    __tablename__ = "daily_trials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, default=date.today, nullable=False, index=True)

    trials_used = Column(Integer, default=0, nullable=False)
    extra_trials_purchased = Column(Integer, default=0, nullable=False)
    life_refills_purchased = Column(Integer, default=0, nullable=False)

    user = relationship("User")