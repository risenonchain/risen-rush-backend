from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased
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
)

router = APIRouter(prefix="/league", tags=["League"])

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

@router.post("/events/{league_id}/register", response_model=LeagueRegistrationSchema)
def register_for_league(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(LeagueRegistration).filter_by(league_id=league_id, user_id=current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already registered for this league")
    participant_count = db.query(LeagueParticipant).filter_by(league_id=league_id).count()
    if participant_count >= 20:
        raise HTTPException(status_code=400, detail="League registration full. Try next month.")
    reg = LeagueRegistration(league_id=league_id, user_id=current_user.id, registered_at=datetime.utcnow(), status='pending')
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg

@router.get("/events/{league_id}/registrations", response_model=List[LeagueRegistrationSchema])
def list_league_registrations(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    results = db.query(LeagueRegistration, User.username).join(User, LeagueRegistration.user_id == User.id).filter(LeagueRegistration.league_id == league_id).all()
    regs = []
    for r, uname in results:
        r.username = uname
        regs.append(r)
    return regs

@router.post("/events/{league_id}/registrations/{registration_id}/approve", response_model=LeagueRegistrationSchema)
def approve_league_registration(league_id: int, registration_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    reg = db.query(LeagueRegistration).filter_by(id=registration_id, league_id=league_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status == "approved":
        return reg
    participant_count = db.query(LeagueParticipant).filter_by(league_id=league_id).count()
    if participant_count >= 20:
        raise HTTPException(status_code=400, detail="League already has 20 participants")
    reg.status = "approved"
    db.add(reg)
    participant = LeagueParticipant(league_id=league_id, user_id=reg.user_id, approved_at=datetime.utcnow())
    db.add(participant)
    db.commit()
    db.refresh(reg)
    return reg

@router.get("/events/{league_id}/participants", response_model=List[LeagueParticipantSchema])
def list_league_participants(league_id: int, db: Session = Depends(get_db)):
    results = db.query(LeagueParticipant, User.username).join(User, LeagueParticipant.user_id == User.id).filter(LeagueParticipant.league_id == league_id).all()
    parts = []
    for p, uname in results:
        p.username = uname
        parts.append(p)
    return parts

@router.post("/events/{league_id}/fixtures/generate", response_model=List[LeagueFixtureSchema])
def auto_generate_fixtures(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    participants = db.query(LeagueParticipant).filter_by(league_id=league_id, status="active").all()
    user_ids = [p.user_id for p in participants]
    if len(user_ids) < 2:
        raise HTTPException(status_code=400, detail="Not enough participants to generate fixtures")
    random.shuffle(user_ids)
    fixtures = []
    round_num = 1
    for i in range(0, len(user_ids) - 1, 2):
        player1 = user_ids[i]
        player2 = user_ids[i+1]
        fix = LeagueFixture(league_id=league_id, round=round_num, player1_id=player1, player2_id=player2)
        db.add(fix)
        db.flush()
        match = LeagueMatch(fixture_id=fix.id)
        db.add(match)
        fixtures.append(fix)
    db.commit()
    for fix in fixtures:
        db.refresh(fix)
    return list_fixtures(league_id, db)

@router.get("/events/{league_id}/fixtures", response_model=List[LeagueFixtureSchema])
def list_fixtures(league_id: int, db: Session = Depends(get_db)):
    u1 = aliased(User)
    u2 = aliased(User)
    results = db.query(LeagueFixture, u1.username.label("u1name"), u2.username.label("u2name")).join(u1, LeagueFixture.player1_id == u1.id).join(u2, LeagueFixture.player2_id == u2.id).filter(LeagueFixture.league_id == league_id).all()
    fixtures = []
    for f, un1, un2 in results:
        f.player1_username = un1
        f.player2_username = un2
        fixtures.append(f)
    return fixtures

@router.get("/events/{league_id}/standings", response_model=List[LeagueStandingSchema])
def get_standings(league_id: int, db: Session = Depends(get_db)):
    results = db.query(LeagueStanding, User.username).join(User, LeagueStanding.user_id == User.id).filter(LeagueStanding.league_id == league_id).order_by(LeagueStanding.points.desc()).all()
    standings = []
    for s, uname in results:
        s.username = uname
        standings.append(s)
    return standings

@router.get("/events/{league_id}/top-scores", response_model=List[LeagueTopScoreSchema])
def get_top_scores(league_id: int, db: Session = Depends(get_db)):
    results = db.query(LeagueTopScore, User.username).join(User, LeagueTopScore.user_id == User.id).filter(LeagueTopScore.league_id == league_id).order_by(LeagueTopScore.score.desc()).limit(10).all()
    scores = []
    for s, uname in results:
        s.username = uname
        scores.append(s)
    return scores

@router.get("/events/{league_id}/deepest-runners", response_model=List[LeagueDeepestRunnerSchema])
def get_deepest_runners(league_id: int, db: Session = Depends(get_db)):
    results = db.query(LeagueDeepestRunner, User.username).join(User, LeagueDeepestRunner.user_id == User.id).filter(LeagueDeepestRunner.league_id == league_id).order_by(LeagueDeepestRunner.level_reached.desc()).limit(10).all()
    runners = []
    for r, uname in results:
        r.username = uname
        runners.append(r)
    return runners

@router.post("/events/{league_id}/participants/{user_id}/disqualify")
def disqualify_participant(league_id: int, user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    participant = db.query(LeagueParticipant).filter_by(league_id=league_id, user_id=user_id).first()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")
    participant.status = "disqualified"
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
    db.commit()
    return {"user_id": user_id, "status": "eliminated"}

@router.get("/events/{league_id}/check-live-access")
def check_live_access(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Admins and participants always have access
    if current_user.is_admin:
        return {"has_access": True}

    participant = db.query(LeagueParticipant).filter_by(league_id=league_id, user_id=current_user.id).first()
    if participant:
        return {"has_access": True}

    # Check if purchased
    access = db.query(LeagueLiveAccess).filter_by(league_id=league_id, user_id=current_user.id).first()
    return {"has_access": bool(access)}
