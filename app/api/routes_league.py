from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, aliased
from typing import List, Optional
from datetime import datetime
import random

from app.db.database import get_db
from app.models.league import (
    LeagueEvent, LeagueRegistration, LeagueParticipant,
    LeagueFixture, LeagueMatch, LeagueStanding,
    LeagueTopScore, LeagueDeepestRunner, LeagueAdminAudit,
    LeagueLiveAccess
)
from app.models.user import User
from app.api.routes_auth import get_current_user
from app.schemas.league import (
    LeagueEvent as LeagueEventSchema,
    LeagueEventCreate,
    LeagueEventUpdate,
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

@router.get("/events/{league_id}/my-status")
def get_my_league_status(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check registration
    reg = db.query(LeagueRegistration).filter_by(league_id=league_id, user_id=current_user.id).first()
    # Check participant
    part = db.query(LeagueParticipant).filter_by(league_id=league_id, user_id=current_user.id).first()

    status = "none"
    if part:
        status = part.status # 'active', 'disqualified', etc.
    elif reg:
        status = "registered" if reg.status == "approved" else "pending"

    return {"status": status, "registration": reg, "participant": part}

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
def toggle_league_event_active(
    event_id: int,
    is_active: Optional[bool] = Query(None),
    update_data: Optional[LeagueEventUpdate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    event = db.query(LeagueEvent).filter_by(id=event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="League event not found")

    # Handle query param (backward compatibility)
    if is_active is not None:
        event.is_active = is_active

    # Handle JSON body (new "Sync Broadcast Protocol" logic)
    if update_data:
        if update_data.is_active is not None:
            event.is_active = update_data.is_active
        if update_data.is_live_visible is not None:
            event.is_live_visible = update_data.is_live_visible
        if update_data.live_fee_usd is not None:
            event.live_fee_usd = update_data.live_fee_usd

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

@router.get("/events/{league_id}/matches", response_model=List[LeagueMatchSchema])
def list_league_matches(league_id: int, db: Session = Depends(get_db)):
    # Join matches with fixtures to filter by league_id
    matches = db.query(LeagueMatch).join(LeagueFixture).filter(LeagueFixture.league_id == league_id).all()
    return matches

@router.get("/events/{league_id}/fixtures", response_model=List[LeagueFixtureSchema])
def list_fixtures(league_id: int, db: Session = Depends(get_db)):
    u1 = aliased(User)
    u2 = aliased(User)
    # Join with LeagueMatch to get the match_id if it exists
    results = db.query(
        LeagueFixture,
        u1.username.label("u1name"),
        u2.username.label("u2name"),
        LeagueMatch.id.label("match_id")
    ).join(u1, LeagueFixture.player1_id == u1.id)\
     .join(u2, LeagueFixture.player2_id == u2.id)\
     .outerjoin(LeagueMatch, LeagueMatch.fixture_id == LeagueFixture.id)\
     .filter(LeagueFixture.league_id == league_id).all()

    fixtures = []
    for f, un1, un2, m_id in results:
        f.player1_username = un1
        f.player2_username = un2
        f.match_id = m_id
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

@router.get("/events/{league_id}/audit", response_model=List[LeagueAdminAuditSchema])
@router.get("/events/{league_id}/admin-audit", response_model=List[LeagueAdminAuditSchema])
def list_league_audit(league_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(LeagueAdminAudit).filter_by(league_id=league_id).order_by(LeagueAdminAudit.created_at.desc()).all()

@router.post("/events/{league_id}/fixtures/{match_id}/force-complete")
def force_complete_league_match(
    league_id: int,
    match_id: int,
    winner_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.league_service import force_complete_match
    match = force_complete_match(db, match_id, winner_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Audit log
    audit = LeagueAdminAudit(
        admin_id=current_user.id,
        action="FORCE_COMPLETE_MATCH",
        league_id=league_id,
        details=f"Match {match_id} force closed. Winner: {winner_id}",
        created_at=datetime.utcnow()
    )
    db.add(audit)
    db.commit()

    return {"message": "Match force completed", "match_id": match_id}

@router.post("/events/{league_id}/group/generate")
def generate_group_stage(
    league_id: int,
    groups_count: int = 4,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    participants = db.query(LeagueParticipant).filter_by(league_id=league_id, status="active").all()
    if not participants:
        raise HTTPException(status_code=400, detail="No active participants")

    user_ids = [p.user_id for p in participants]
    random.shuffle(user_ids)

    # Divide into groups
    groups = [[] for _ in range(groups_count)]
    for i, uid in enumerate(user_ids):
        groups[i % groups_count].append(uid)

    fixtures_created = 0
    for g_idx, members in enumerate(groups):
        group_name = chr(65 + g_idx) # A, B, C, D...
        # Round robin within group
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                p1, p2 = members[i], members[j]
                fix = LeagueFixture(
                    league_id=league_id,
                    round=1,
                    player1_id=p1,
                    player2_id=p2,
                    stage="group",
                    group_name=group_name
                )
                db.add(fix)
                db.flush()
                match = LeagueMatch(fixture_id=fix.id)
                db.add(match)
                fixtures_created += 1

    db.commit()
    return {"message": f"Generated {fixtures_created} group stage fixtures across {groups_count} groups"}

@router.post("/events/{league_id}/knockout/generate")
def generate_knockout_stage(
    league_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Take top 8 players overall from standings as default knockout qualifier
    top_standings = db.query(LeagueStanding).filter_by(league_id=league_id).order_by(LeagueStanding.points.desc()).limit(8).all()
    qualified_ids = [s.user_id for s in top_standings]

    if len(qualified_ids) < 2:
        # Fallback to active participants if no standings yet
        participants = db.query(LeagueParticipant).filter_by(league_id=league_id, status="active").all()
        qualified_ids = [p.user_id for p in participants]
        random.shuffle(qualified_ids)

    if len(qualified_ids) < 2:
        raise HTTPException(status_code=400, detail="Not enough participants for knockout")

    # Determine next round number
    last_fix = db.query(LeagueFixture).filter_by(league_id=league_id).order_by(LeagueFixture.round.desc()).first()
    next_round = (last_fix.round + 1) if last_fix else 1

    fixtures_created = 0
    for i in range(0, len(qualified_ids) - 1, 2):
        fix = LeagueFixture(
            league_id=league_id,
            round=next_round,
            player1_id=qualified_ids[i],
            player2_id=qualified_ids[i+1],
            stage="knockout"
        )
        db.add(fix)
        db.flush()
        match = LeagueMatch(fixture_id=fix.id)
        db.add(match)
        fixtures_created += 1

    db.commit()
    return {"message": f"Generated {fixtures_created} knockout fixtures for Round {next_round}"}


