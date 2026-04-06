import secrets
from datetime import datetime, timezone

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.routes_auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models.game_session import GameSession
from app.models.point_wallet import PointWallet
from app.models.referral_reward import ReferralReward
from app.models.user import User
#from app.models.user_device import UserDevice
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
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def get_request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def verify_turnstile_or_raise(request: Request, action: str) -> None:
    if not settings.turnstile_enabled:
        return

    token = request.headers.get("X-Turnstile-Token")
    if not token:
        raise HTTPException(
            status_code=400,
            detail=f"Turnstile verification is required for {action}",
        )

    remoteip = get_request_ip(request)

    try:
        response = requests.post(
            TURNSTILE_VERIFY_URL,
            data={
                "secret": settings.turnstile_secret_key,
                "response": token,
                "remoteip": remoteip,
            },
            timeout=10,
        )
        result = response.json()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Turnstile verification service is unavailable",
        )

    if not result.get("success", False):
        raise HTTPException(
            status_code=400,
            detail="Turnstile verification failed",
        )


def bind_or_validate_device(
    user: User,
    device_fingerprint: str,
    request_ip: str | None,
    db: Session,
) -> None:
    existing_binding = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == user.id)
        .first()
    )

    if existing_binding:
        if existing_binding.device_fingerprint != device_fingerprint:
            raise HTTPException(
                status_code=403,
                detail="This account is locked to another device",
            )

        existing_binding.last_ip = request_ip
        existing_binding.last_seen_at = datetime.utcnow()
        db.add(existing_binding)
        db.flush()
        return

    conflict_binding = (
        db.query(UserDevice)
        .filter(UserDevice.device_fingerprint == device_fingerprint)
        .first()
    )

    if conflict_binding and conflict_binding.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Maximum device limit exceeded for this device",
        )

    new_binding = UserDevice(
        user_id=user.id,
        device_fingerprint=device_fingerprint,
        first_ip=request_ip,
        last_ip=request_ip,
    )
    db.add(new_binding)
    db.flush()


def maybe_grant_referral_reward(
    current_user: User,
    device_fingerprint: str,
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

    referrer_device = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == referrer.id)
        .first()
    )

    if referrer_device and referrer_device.device_fingerprint == device_fingerprint:
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
    # ❌ REMOVED: verify_turnstile_or_raise(request, "session start")

    request_ip = get_request_ip(request)

    bind_or_validate_device(
        user=current_user,
        device_fingerprint=payload.device_fingerprint,
        request_ip=request_ip,
        db=db,
    )

    remaining = get_remaining_trials(current_user.id, db)

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
