
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import random

from app.db.database import get_db
from app.models.league import (
    LeagueEvent, LeagueRegistration, LeagueParticipant,
    LeagueFixture, LeagueMatch, LeagueStanding,
    LeagueTopScore, LeagueDeepestRunner, LeagueAdminAudit
)
from app.models.user import User
from app.api.routes_auth import get_current_user
from app.schemas.league import (
    LeagueEvent as LeagueEventSchema,
    LeagueEventCreate,
    LeagueRegistration as LeagueRegistrationSchema,
    LeagueRegistrationCreate,
    LeagueParticipant as LeagueParticipantSchema,
    LeagueParticipantCreate,
    LeagueFixture as LeagueFixtureSchema,
    LeagueFixtureCreate,
    LeagueMatch as LeagueMatchSchema,
    LeagueMatchCreate,
    LeagueStanding as LeagueStandingSchema,
    LeagueTopScore as LeagueTopScoreSchema,
    LeagueDeepestRunner as LeagueDeepestRunnerSchema,
    LeagueAdminAudit as LeagueAdminAuditSchema,
    # ... add others as needed
)

router = APIRouter(prefix="/league", tags=["League"])

# --- Disqualify or Eliminate League Participant ---
@router.post("/events/{league_id}/participants/{user_id}/disqualify")
def disqualify_participant(league_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    participant = db.query(LeagueParticipant).filter_by(league_id=league_id, user_id=user_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    participant.status = "disqualified"
    db.add(participant)
    db.commit()
    return {"user_id": user_id, "status": "disqualified"}

@router.post("/events/{league_id}/participants/{user_id}/eliminate")
def eliminate_participant(league_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    participant = db.query(LeagueParticipant).filter_by(league_id=league_id, user_id=user_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    participant.status = "eliminated"
    db.add(participant)
    db.commit()
    return {"user_id": user_id, "status": "eliminated"}
# --- Finals Progression Logic ---
@router.post("/events/{league_id}/finals/generate")
def generate_finals(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Get group winners from previous endpoint or standings
    group_fixtures = db.query(LeagueFixture).filter_by(league_id=league_id, stage="group_complete").all()
    group_winners = set()
    for fix in group_fixtures:
        matches = db.query(LeagueMatch).filter_by(fixture_id=fix.id).all()
        win_count = {}
        for m in matches:
            if m.winner_id:
                win_count[m.winner_id] = win_count.get(m.winner_id, 0) + 1
        if win_count:
            max_wins = max(win_count.values())
            winners = [uid for uid, w in win_count.items() if w == max_wins]
            group_winners.update(winners)
    group_winners = list(group_winners)
    if len(group_winners) < 2:
        raise HTTPException(status_code=400, detail="Not enough group winners for finals")
    # Shuffle and pair for semifinals/finals
    import random
    random.shuffle(group_winners)
    fixtures = []
    round_num = 1
    stage = "semifinal" if len(group_winners) > 2 else "final"
    for i in range(0, len(group_winners) - 1, 2):
        player1 = group_winners[i]
        player2 = group_winners[i+1]
        fix = LeagueFixture(league_id=league_id, round=round_num, player1_id=player1, player2_id=player2, stage=stage)
        db.add(fix)
        fixtures.append(fix)
    db.commit()
    for fix in fixtures:
        db.refresh(fix)
    return {"final_fixtures": [f.id for f in fixtures], "stage": stage}
# --- Group Stage Progression Logic ---
@router.post("/events/{league_id}/group/progress")
def progress_group_stage(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    # Find all group fixtures
    group_fixtures = db.query(LeagueFixture).filter_by(league_id=league_id, stage="group").all()
    if not group_fixtures:
        raise HTTPException(status_code=400, detail="No group fixtures found")
    # Find all groups
    groups = {}
    for fix in group_fixtures:
        if fix.group_name not in groups:
            groups[fix.group_name] = []
        groups[fix.group_name].append(fix)
    # For each group, determine winner(s) and mark group as complete
    group_winners = []
    for group, fixtures in groups.items():
        # Only progress if all matches in group are submitted
        if not all(f.result_submitted for f in fixtures):
            continue
        # Tally wins per user in group
        win_count = {}
        for fix in fixtures:
            matches = db.query(LeagueMatch).filter_by(fixture_id=fix.id).all()
            for m in matches:
                if m.winner_id:
                    win_count[m.winner_id] = win_count.get(m.winner_id, 0) + 1
        if not win_count:
            continue
        # Find user(s) with most wins
        max_wins = max(win_count.values())
        winners = [uid for uid, w in win_count.items() if w == max_wins]
        group_winners.extend(winners)
        # Optionally: mark group as complete (custom logic)
        for fix in fixtures:
            fix.stage = "group_complete"
            db.add(fix)
    db.commit()
    return {"group_winners": group_winners, "groups": list(groups.keys())}


# --- League Events ---
@router.post("/events", response_model=LeagueEventSchema)
def create_league_event(event: LeagueEventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    db_event = LeagueEvent(**event.dict(), created_at=datetime.utcnow())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.get("/events", response_model=List[LeagueEventSchema])
def list_league_events(db: Session = Depends(get_db)):
    return db.query(LeagueEvent).order_by(LeagueEvent.start_date.desc()).all()

# --- Toggle League Event Active Status ---
@router.patch("/events/{event_id}/active", response_model=LeagueEventSchema)
def toggle_league_event_active(event_id: int, is_active: bool, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    event = db.query(LeagueEvent).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="League event not found")
    event.is_active = is_active
    db.commit()
    db.refresh(event)
    return event

# --- League Registration ---
@router.post("/events/{league_id}/register", response_model=LeagueRegistrationSchema)
def register_for_league(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if already registered
    existing = db.query(LeagueRegistration).filter_by(league_id=league_id, user_id=current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this league")
    # Check participant limit
    participant_count = db.query(LeagueParticipant).filter_by(league_id=league_id).count()
    if participant_count >= 20:
        raise HTTPException(status_code=400, detail="League registration full. Try next month.")
    reg = LeagueRegistration(
        league_id=league_id,
        user_id=current_user.id,
        registered_at=datetime.utcnow(),
        status='pending'
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


@router.get("/events/{league_id}/registrations", response_model=List[LeagueRegistrationSchema])
def list_league_registrations(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(LeagueRegistration).filter_by(league_id=league_id).all()

# --- Approve League Registration ---
@router.post("/events/{league_id}/registrations/{registration_id}/approve", response_model=LeagueRegistrationSchema)
def approve_league_registration(league_id: int, registration_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    reg = db.query(LeagueRegistration).filter_by(id=registration_id, league_id=league_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status == "approved":
        return reg
    # Enforce 20-player limit
    participant_count = db.query(LeagueParticipant).filter_by(league_id=league_id).count()
    if participant_count >= 20:
        raise HTTPException(status_code=400, detail="League already has 20 participants")
    # Approve registration and add to participants
    reg.status = "approved"
    db.add(reg)
    db.commit()
    db.refresh(reg)
    participant = LeagueParticipant(league_id=league_id, user_id=reg.user_id, approved_at=datetime.utcnow())
    db.add(participant)
    db.commit()
    return reg

# --- League Participants ---
@router.get("/events/{league_id}/participants", response_model=List[LeagueParticipantSchema])
def list_league_participants(league_id: int, db: Session = Depends(get_db)):
    return db.query(LeagueParticipant).filter_by(league_id=league_id).all()


# --- League Fixtures ---
from app.schemas.league import LeagueFixture as LeagueFixtureSchema, LeagueFixtureCreate


# --- Auto-generate random fixtures for all approved participants ---
import random
@router.post("/events/{league_id}/fixtures/generate", response_model=List[LeagueFixtureSchema])
def auto_generate_fixtures(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    participants = db.query(LeagueParticipant).filter_by(league_id=league_id).all()
    user_ids = [p.user_id for p in participants]
    if len(user_ids) < 2:
        raise HTTPException(status_code=400, detail="Not enough participants to generate fixtures")
    random.shuffle(user_ids)
    fixtures = []
    round_num = 1
    # Pair up users for round-robin (single round)
    for i in range(0, len(user_ids) - 1, 2):
        player1 = user_ids[i]
        player2 = user_ids[i+1]
        fix = LeagueFixture(league_id=league_id, round=round_num, player1_id=player1, player2_id=player2)
        db.add(fix)
        fixtures.append(fix)
    # If odd number, last user gets a bye (no match)
    db.commit()
    for fix in fixtures:
        db.refresh(fix)
    return fixtures

@router.get("/events/{league_id}/fixtures", response_model=List[LeagueFixtureSchema])
def list_fixtures(league_id: int, db: Session = Depends(get_db)):
    return db.query(LeagueFixture).filter_by(league_id=league_id).all()

# --- League Matches ---
from app.schemas.league import LeagueMatch as LeagueMatchSchema, LeagueMatchCreate

@router.post("/matches", response_model=LeagueMatchSchema)
def submit_match_result(match: LeagueMatchCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_match = LeagueMatch(**match.dict(), played_at=datetime.utcnow())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match

@router.get("/events/{league_id}/matches", response_model=List[LeagueMatchSchema])
def list_matches(league_id: int, db: Session = Depends(get_db)):
    fixtures = db.query(LeagueFixture.id).filter_by(league_id=league_id).all()
    fixture_ids = [f.id for f in fixtures]
    return db.query(LeagueMatch).filter(LeagueMatch.fixture_id.in_(fixture_ids)).all()

# --- League Standings ---
from app.schemas.league import LeagueStanding as LeagueStandingSchema

@router.get("/events/{league_id}/standings", response_model=List[LeagueStandingSchema])
def get_standings(league_id: int, db: Session = Depends(get_db)):
    return db.query(LeagueStanding).filter_by(league_id=league_id).order_by(LeagueStanding.points.desc()).all()

# --- League Top Scores ---
from app.schemas.league import LeagueTopScore as LeagueTopScoreSchema

@router.get("/events/{league_id}/top-scores", response_model=List[LeagueTopScoreSchema])
def get_top_scores(league_id: int, db: Session = Depends(get_db)):
    return db.query(LeagueTopScore).filter_by(league_id=league_id).order_by(LeagueTopScore.score.desc()).limit(10).all()

# --- League Deepest Runners ---
from app.schemas.league import LeagueDeepestRunner as LeagueDeepestRunnerSchema

@router.get("/events/{league_id}/deepest-runners", response_model=List[LeagueDeepestRunnerSchema])
def get_deepest_runners(league_id: int, db: Session = Depends(get_db)):
    return db.query(LeagueDeepestRunner).filter_by(league_id=league_id).order_by(LeagueDeepestRunner.level_reached.desc()).limit(10).all()

# --- League Admin Audit Log ---
from app.schemas.league import LeagueAdminAudit as LeagueAdminAuditSchema

@router.get("/events/{league_id}/admin-audit", response_model=List[LeagueAdminAuditSchema])
def get_admin_audit(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(LeagueAdminAudit).filter_by(league_id=league_id).order_by(LeagueAdminAudit.created_at.desc()).all()
