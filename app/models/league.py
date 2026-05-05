from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime, Date, UniqueConstraint, Text
from app.db.base import Base

class LeagueEvent(Base):
    __tablename__ = "league_events"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False)
    is_live_visible = Column(Boolean, default=False) # Admin toggle for live viewing
    live_fee_usd = Column(Integer, default=30) # Cents, e.g. 30 = $0.30
    created_at = Column(DateTime)

class LeagueLiveAccess(Base):
    __tablename__ = "league_live_access"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    match_id = Column(Integer, ForeignKey("league_matches.id"), nullable=True)
    purchased_at = Column(DateTime)
    payment_reference = Column(String(100))

class LeagueRegistration(Base):
    __tablename__ = "league_registrations"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    registered_at = Column(DateTime)
    status = Column(String(20), default='pending')

class LeagueParticipant(Base):
    __tablename__ = "league_participants"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_at = Column(DateTime)
    status = Column(String, default="active")  # NEW: 'active', 'disqualified', 'eliminated'
    __table_args__ = (UniqueConstraint('league_id', 'user_id', name='_league_user_uc'),)

class LeagueFixture(Base):
    __tablename__ = "league_fixtures"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    round = Column(Integer, nullable=False)
    player1_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    player2_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scheduled_at = Column(DateTime)
    result_submitted = Column(Boolean, default=False)
    stage = Column(String, default="group")  # NEW: 'group', 'semifinal', 'final', etc.
    group_name = Column(String, nullable=True)  # NEW: for group stage

class LeagueMatch(Base):
    __tablename__ = "league_matches"
    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("league_fixtures.id"))
    player1_score = Column(Integer)
    player2_score = Column(Integer)
    winner_id = Column(Integer, ForeignKey("users.id"))
    played_at = Column(DateTime)

class LeagueTopScore(Base):
    __tablename__ = "league_top_scores"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    match_id = Column(Integer, ForeignKey("league_matches.id"))
    created_at = Column(DateTime)

class LeagueDeepestRunner(Base):
    __tablename__ = "league_deepest_runners"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level_reached = Column(Integer, nullable=False)
    match_id = Column(Integer, ForeignKey("league_matches.id"))
    created_at = Column(DateTime)

class LeagueStanding(Base):
    __tablename__ = "league_standings"
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    matches_played = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    points = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    created_at = Column(DateTime)

class LeagueAdminAudit(Base):
    __tablename__ = "league_admin_audit"
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(255), nullable=False)
    league_id = Column(Integer, ForeignKey("league_events.id"))
    details = Column(Text)
    created_at = Column(DateTime)