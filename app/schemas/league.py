from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

# --- League Event ---
class LeagueEventBase(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_active: Optional[bool] = False
    is_live_visible: Optional[bool] = False
    live_fee_usd: Optional[int] = 30

class LeagueEventCreate(LeagueEventBase):
    pass

class LeagueEvent(LeagueEventBase):
    id: int
    created_at: Optional[datetime]
    class Config:
        orm_mode = True

# --- League Registration ---
class LeagueRegistrationBase(BaseModel):
    league_id: int
    user_id: int
    status: Optional[str] = 'pending'

class LeagueRegistrationCreate(LeagueRegistrationBase):
    pass

class LeagueRegistration(LeagueRegistrationBase):
    id: int
    registered_at: Optional[datetime]
    username: Optional[str] = None
    class Config:
        orm_mode = True

# --- League Participant ---
class LeagueParticipantBase(BaseModel):
    league_id: int
    user_id: int

class LeagueParticipantCreate(LeagueParticipantBase):
    pass

class LeagueParticipant(LeagueParticipantBase):
    id: int
    approved_at: Optional[datetime]
    username: Optional[str] = None
    status: Optional[str] = "active"
    class Config:
        orm_mode = True

# --- League Fixture ---
class LeagueFixtureBase(BaseModel):
    league_id: int
    round: int
    player1_id: int
    player2_id: int
    scheduled_at: Optional[datetime]

class LeagueFixtureCreate(LeagueFixtureBase):
    pass

class LeagueFixture(LeagueFixtureBase):
    id: int
    result_submitted: Optional[bool] = False
    player1_username: Optional[str] = None
    player2_username: Optional[str] = None
    class Config:
        orm_mode = True

# --- League Match ---
class LeagueMatchBase(BaseModel):
    fixture_id: int
    player1_score: Optional[int]
    player2_score: Optional[int]
    winner_id: Optional[int]

class LeagueMatchCreate(LeagueMatchBase):
    pass

class LeagueMatch(LeagueMatchBase):
    id: int
    played_at: Optional[datetime]
    class Config:
        orm_mode = True

# --- League Top Score ---
class LeagueTopScoreBase(BaseModel):
    league_id: int
    user_id: int
    score: int
    match_id: Optional[int]

class LeagueTopScoreCreate(LeagueTopScoreBase):
    pass

class LeagueTopScore(LeagueTopScoreBase):
    id: int
    created_at: Optional[datetime]
    username: Optional[str] = None
    class Config:
        orm_mode = True

# --- League Deepest Runner ---
class LeagueDeepestRunnerBase(BaseModel):
    league_id: int
    user_id: int
    level_reached: int
    match_id: Optional[int]

class LeagueDeepestRunnerCreate(LeagueDeepestRunnerBase):
    pass

class LeagueDeepestRunner(LeagueDeepestRunnerBase):
    id: int
    created_at: Optional[datetime]
    username: Optional[str] = None
    class Config:
        orm_mode = True

# --- League Standing ---
class LeagueStandingBase(BaseModel):
    league_id: int
    user_id: int
    matches_played: Optional[int] = 0
    wins: Optional[int] = 0
    losses: Optional[int] = 0
    draws: Optional[int] = 0
    points: Optional[int] = 0
    goals_for: Optional[int] = 0
    goals_against: Optional[int] = 0

class LeagueStandingCreate(LeagueStandingBase):
    pass

class LeagueStanding(LeagueStandingBase):
    id: int
    created_at: Optional[datetime]
    username: Optional[str] = None
    class Config:
        orm_mode = True

# --- League Admin Audit ---
class LeagueAdminAuditBase(BaseModel):
    admin_id: int
    action: str
    league_id: Optional[int]
    details: Optional[str]

class LeagueAdminAuditCreate(LeagueAdminAuditBase):
    pass

class LeagueAdminAudit(LeagueAdminAuditBase):
    id: int
    created_at: Optional[datetime]
    class Config:
        orm_mode = True
