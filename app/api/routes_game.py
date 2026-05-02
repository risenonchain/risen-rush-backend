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

router = APIRouter(prefix="/rush", tags=["RISEN Rush"])

STARTING_LIVES = 3
REFERRAL_REWARD_VAULT_TRIALS = 1


def maybe_grant_referral_reward(
    current_user: User,
    db: Session,
) -> None:
    if not current_user.referred_by_user_id:
        return

    if current_user.referred_by_user_id == current_user.id:
        return

    existing_reward = (
        db.query(ReferralReward)
        .filter(ReferralReward.referred_user_id == current_user.id)
        .first()
    )
    if existing_reward:
        return

    completed_sessions = (
        db.query(GameSession)
        .filter(
            GameSession.user_id == current_user.id,
            GameSession.status == "finished",
        )
        .count()
    )

    if completed_sessions != 1:
        return

    referrer = (
        db.query(User)
        .filter(User.id == current_user.referred_by_user_id)
        .first()
    )
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

    # Premium users can always start a session
    if current_user.is_premium:
        success, trial_source = True, "premium"
    else:
        if remaining <= 0:
            raise HTTPException(status_code=403, detail="No trials remaining today")
        success, trial_source = consume_trial(current_user.id, db)
        if not success:
            raise HTTPException(status_code=403, detail="Trial limit reached")

    token = secrets.token_hex(16)

    session = GameSession(
        user_id=current_user.id,
        session_token=token,
        status="active",
    )

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
    session = (
        db.query(GameSession)
        .filter(
            GameSession.id == payload.session_id,
            GameSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already finished")

    if payload.final_score < 0:
        raise HTTPException(status_code=400, detail="Final score cannot be negative")

    if payload.duration_seconds < 0:
        raise HTTPException(status_code=400, detail="Duration cannot be negative")

    if payload.level_reached < 1:
        raise HTTPException(status_code=400, detail="Level reached must be at least 1")

    if payload.lives_remaining < 0 or payload.lives_remaining > STARTING_LIVES:
        raise HTTPException(status_code=400, detail="Invalid lives remaining value")

    session.final_score = payload.final_score
    session.duration_seconds = payload.duration_seconds
    session.level_reached = payload.level_reached
    session.lives_remaining = payload.lives_remaining
    session.ended_at = datetime.now(timezone.utc)
    session.status = "finished"

    wallet = (
        db.query(PointWallet)
        .filter(PointWallet.user_id == current_user.id)
        .first()
    )

    if not wallet:
        wallet = PointWallet(
            user_id=current_user.id,
            total_points_earned=0,
            available_points=0,
            claimed_points=0,
        )
        db.add(wallet)
        db.flush()

    wallet.total_points_earned += payload.final_score
    wallet.available_points += payload.final_score

    db.add(session)
    db.add(wallet)

    if payload.final_score > 0:
        maybe_grant_referral_reward(
            current_user=current_user,
            db=db,
        )

    db.commit()

    return {
        "message": "Session recorded",
        "points_added": payload.final_score,
        "wallet_points": wallet.available_points,
    }


@router.get("/wallet", response_model=WalletResponse)
def get_wallet(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = (
        db.query(PointWallet)
        .filter(PointWallet.user_id == current_user.id)
        .first()
    )

    if not wallet:
        wallet = PointWallet(
            user_id=current_user.id,
            total_points_earned=0,
            available_points=0,
            claimed_points=0,
        )
        db.add(wallet)
        db.commit()
        db.refresh(wallet)

    return WalletResponse(
        total_points_earned=wallet.total_points_earned,
        available_points=wallet.available_points,
        claimed_points=wallet.claimed_points,
        vault_trials=current_user.vault_trials or 0,
    )
