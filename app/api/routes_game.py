import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.routes_auth import get_current_user
from app.db.database import get_db
from app.models.game_session import GameSession
from app.models.point_wallet import PointWallet
from app.models.referral_reward import ReferralReward
from app.models.user import User
from app.models.league import LeagueParticipant, LeagueMatch, LeagueFixture, LeagueTopScore, LeagueDeepestRunner, LeagueChallenge
from app.schemas.game import (
    FinishSessionRequest,
    StartSessionRequest,
    StartSessionResponse,
    WalletResponse,
)
from app.services.trial_service import (
    consume_trial,
    get_daily_trials_remaining,
    get_remaining_trials,
    get_vault_trials_remaining,
)
from app.services.league_service import process_match_completion

router = APIRouter(prefix="/rush", tags=["RISEN Rush"])

STARTING_LIVES = 3
REFERRAL_REWARD_VAULT_TRIALS = 1

def maybe_grant_referral_reward(current_user: User, db: Session) -> None:
    if not current_user.referred_by_user_id or current_user.referred_by_user_id == current_user.id:
        return
    existing_reward = db.query(ReferralReward).filter(ReferralReward.referred_user_id == current_user.id).first()
    if existing_reward:
        return
    completed_sessions = db.query(GameSession).filter(GameSession.user_id == current_user.id, GameSession.status == "finished").count()
    if completed_sessions != 1:
        return
    referrer = db.query(User).filter(User.id == current_user.referred_by_user_id).first()
    if not referrer:
        return
    reward = ReferralReward(
        referrer_user_id=referrer.id,
        referred_user_id=current_user.id,
        reward_type="vault_trial",
        reward_value=REFERRAL_REWARD_VAULT_TRIALS,
        status="granted",
    )
    db.add(reward)
    referrer.vault_trials = (referrer.vault_trials or 0) + REFERRAL_REWARD_VAULT_TRIALS
    db.add(referrer)

@router.post("/session/start", response_model=StartSessionResponse)
def start_session(
    payload: StartSessionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    remaining = get_remaining_trials(current_user.id, db)
    if current_user.is_premium:
        success, trial_source = True, "premium"
    else:
        if remaining <= 0:
            raise HTTPException(status_code=403, detail="No trials remaining today")
        success, trial_source = consume_trial(current_user.id, db)
        if not success:
            raise HTTPException(status_code=403, detail="Trial limit reached")
    token = secrets.token_hex(16)
    session = GameSession(user_id=current_user.id, session_token=token, status="active")
    db.add(session)
    db.commit()
    db.refresh(session)
    return StartSessionResponse(
        session_id=session.id,
        session_token=session.session_token,
        trials_remaining=get_remaining_trials(current_user.id, db),
        daily_trials_remaining=get_daily_trials_remaining(current_user.id, db),
        vault_trials_remaining=get_vault_trials_remaining(current_user.id, db),
        starting_lives=STARTING_LIVES,
        trial_source=trial_source,
    )

@router.post("/session/finish")
def finish_session(
    payload: FinishSessionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(GameSession).filter(GameSession.id == payload.session_id, GameSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already finished")
    if payload.final_score < 0:
        raise HTTPException(status_code=400, detail="Final score cannot be negative")

    session.final_score = payload.final_score
    session.duration_seconds = payload.duration_seconds
    session.level_reached = payload.level_reached
    session.lives_remaining = payload.lives_remaining
    session.ended_at = datetime.utcnow()
    session.status = "finished"
    db.add(session)

    # Update User Personal Bests
    if payload.final_score > (current_user.best_score or 0):
        current_user.best_score = payload.final_score
    if payload.level_reached > (current_user.best_level or 1):
        current_user.best_level = payload.level_reached
    db.add(current_user)

    wallet = db.query(PointWallet).filter(PointWallet.user_id == current_user.id).first()
    if not wallet:
        wallet = PointWallet(user_id=current_user.id, total_points_earned=0, available_points=0, claimed_points=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    wallet.total_points_earned += payload.final_score
    wallet.available_points += payload.final_score
    db.add(wallet)

    maybe_grant_referral_reward(current_user, db)
    db.commit()
    return {"message": "Session finished, points awarded", "points_earned": payload.final_score}

@router.post("/league/session/start", response_model=StartSessionResponse)
def start_league_session(
    match_id: int,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    match = db.query(LeagueMatch).filter_by(id=match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="League match not found")
    fixture = db.query(LeagueFixture).filter_by(id=match.fixture_id).first()
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    participant = db.query(LeagueParticipant).filter_by(league_id=fixture.league_id, user_id=current_user.id).first()
    if not participant or participant.status != "active":
        raise HTTPException(status_code=403, detail="Not eligible for league match")

    token = secrets.token_hex(16)

    # Determine lives based on stage: 2 for groups, 1 for knockout/finals
    league_lives = 2 if fixture.stage == "group" else 1

    # Record first start time if not already set
    if not fixture.first_start_at:
        fixture.first_start_at = datetime.utcnow()
        db.add(fixture)

    session = GameSession(
        user_id=current_user.id,
        session_token=token,
        status="active",
        lives_remaining=league_lives,
        is_league_game=True,
        league_match_id=match_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return StartSessionResponse(
        session_id=session.id,
        session_token=session.session_token,
        trials_remaining=0,
        daily_trials_remaining=0,
        vault_trials_remaining=0,
        starting_lives=league_lives,
        trial_source="league",
    )


@router.post("/league/challenge/{challenge_id}/start", response_model=StartSessionResponse)
def start_p2p_session(
    challenge_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    challenge = db.query(LeagueChallenge).filter_by(id=challenge_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.status != "accepted":
        raise HTTPException(status_code=400, detail="Challenge must be accepted first")

    if current_user.id not in [challenge.challenger_id, challenge.challenged_id]:
        raise HTTPException(status_code=403, detail="Not a participant in this challenge")

    token = secrets.token_hex(16)

    # P2P survival mode: 2 lives (like group stage)
    p2p_lives = 2

    session = GameSession(
        user_id=current_user.id,
        session_token=token,
        status="active",
        lives_remaining=p2p_lives,
        is_league_game=True,
        is_p2p=True,
        league_challenge_id=challenge_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return StartSessionResponse(
        session_id=session.id,
        session_token=session.session_token,
        trials_remaining=0,
        daily_trials_remaining=0,
        vault_trials_remaining=0,
        starting_lives=p2p_lives,
        trial_source="p2p",
    )

@router.post("/league/session/finish")
def finish_league_session(
    payload: FinishSessionRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(GameSession).filter(GameSession.id == payload.session_id, GameSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already finished")

    session.final_score = payload.final_score
    session.duration_seconds = payload.duration_seconds
    session.level_reached = payload.level_reached
    session.lives_remaining = payload.lives_remaining
    session.ended_at = datetime.utcnow()
    session.status = "finished"
    db.add(session)

    # Update User Personal Bests
    if payload.final_score > (current_user.best_score or 0):
        current_user.best_score = payload.final_score
    if payload.level_reached > (current_user.best_level or 1):
        current_user.best_level = payload.level_reached
    db.add(current_user)

    if session.is_league_game and session.league_match_id:
        match = db.query(LeagueMatch).filter_by(id=session.league_match_id).first()
        if match:
            fixture = db.query(LeagueFixture).filter_by(id=match.fixture_id).first()
            if fixture:
                # Assign score to correct player slot in match
                if fixture.player1_id == current_user.id:
                    match.player1_score = payload.final_score
                elif fixture.player2_id == current_user.id:
                    match.player2_score = payload.final_score

                # Check for Top Scores / Deepest Runners records within this league
                top_score = LeagueTopScore(league_id=fixture.league_id, user_id=current_user.id, score=payload.final_score, match_id=match.id, created_at=datetime.utcnow())
                db.add(top_score)
                deep_run = LeagueDeepestRunner(league_id=fixture.league_id, user_id=current_user.id, level_reached=payload.level_reached, match_id=match.id, created_at=datetime.utcnow())
                db.add(deep_run)

                db.commit()
                # Recalculate match outcome if both scores are in
                process_match_completion(db, match)

    if session.is_p2p and session.league_challenge_id:
        challenge = db.query(LeagueChallenge).filter_by(id=session.league_challenge_id).first()
        if challenge:
            if challenge.challenger_id == current_user.id:
                challenge.challenger_score = payload.final_score
            elif challenge.challenged_id == current_user.id:
                challenge.challenged_score = payload.final_score

            db.add(challenge)
            db.commit()

            from app.services.league_service import process_challenge_completion
            process_challenge_completion(db, challenge)

    db.commit()
    return {"message": "League session recorded"}

@router.get("/wallet", response_model=WalletResponse)
def get_wallet(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(PointWallet).filter(PointWallet.user_id == current_user.id).first()
    if not wallet:
        wallet = PointWallet(user_id=current_user.id, total_points_earned=0, available_points=0, claimed_points=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return WalletResponse(
        total_points_earned=wallet.total_points_earned,
        available_points=wallet.available_points,
        claimed_points=wallet.claimed_points,
        vault_trials=current_user.vault_trials or 0,
    )


@router.get("/players")
def list_available_players(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # List other players for P2P challenges (Prime only feature)
    if not current_user.is_premium:
        raise HTTPException(status_code=403, detail="Prime protocol required")

    # Return basic info of other users
    users = db.query(User).filter(User.id != current_user.id).limit(50).all()
    return [{"id": u.id, "username": u.username, "is_premium": u.is_premium} for u in users]
