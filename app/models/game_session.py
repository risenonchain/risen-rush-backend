from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.db.database import Base


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    session_token = Column(String, unique=True, index=True, nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    duration_seconds = Column(Integer, default=0, nullable=False)
    level_reached = Column(Integer, default=1, nullable=False)
    final_score = Column(Integer, default=0, nullable=False)
    lives_remaining = Column(Integer, default=3, nullable=False)

    status = Column(String, default="active", nullable=False)
    validation_status = Column(String, default="pending", nullable=False)

    is_league_game = Column(Boolean, default=False)  # NEW: True if this is a league game
    league_match_id = Column(Integer, ForeignKey("league_matches.id"), nullable=True)  # NEW: link to league match

    user = relationship("User")