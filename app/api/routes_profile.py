from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.routes_auth import get_current_user
from app.core.security import get_password_hash, verify_password
from app.db.database import get_db
from app.models.game_session import GameSession
from app.models.point_wallet import PointWallet
from app.models.redemption_request import RedemptionRequest
from app.models.referral_reward import ReferralReward
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    MessageResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.schemas.game import (
    RedemptionRequestCreate,
    RedemptionRequestResponse,
    ReferralInfoResponse,
)

router = APIRouter(prefix="/profile", tags=["Profile"])

REDEMPTION_THRESHOLD = 100000


@router.get("/me", response_model=UserResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.username is not None:
        normalized_username = payload.username.strip()
        if len(normalized_username) < 3:
            raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

        existing_user = (
            db.query(User)
            .filter(
                User.username == normalized_username,
                User.id != current_user.id,
            )
            .first()
        )
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = normalized_username

    if payload.wallet_address is not None:
        current_user.wallet_address = payload.wallet_address.strip() or None

    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url.strip() or None

    if payload.generated_avatar_url is not None:
        current_user.generated_avatar_url = payload.generated_avatar_url.strip() or None

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()

    return MessageResponse(message="Password changed successfully")


@router.get("/referral", response_model=ReferralInfoResponse)
def get_referral_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    successful_referrals = (
        db.query(func.count(ReferralReward.id))
        .filter(ReferralReward.referrer_user_id == current_user.id)
        .scalar()
    ) or 0

    referral_link = f"/rush/register?ref={current_user.referral_code or ''}"

    return ReferralInfoResponse(
        referral_code=current_user.referral_code or "",
        referral_link=referral_link,
        vault_trials=current_user.vault_trials or 0,
        successful_referrals=int(successful_referrals),
    )


@router.post("/redemptions/request", response_model=RedemptionRequestResponse)
def create_redemption_request(
    payload: RedemptionRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = (
        db.query(PointWallet)
        .filter(PointWallet.user_id == current_user.id)
        .first()
    )

    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found")

    wallet_address = payload.wallet_address.strip()
    if not wallet_address:
        raise HTTPException(status_code=400, detail="Wallet address is required")

    if wallet.available_points < REDEMPTION_THRESHOLD:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum redemption threshold is {REDEMPTION_THRESHOLD} points",
        )

    if payload.points_requested > wallet.available_points:
        raise HTTPException(
            status_code=400,
            detail="Requested points exceed available wallet points",
        )


    # --- Monetization logic: Standard users limited to 1 redemption per month ---
    from datetime import datetime
    from sqlalchemy import extract

    if not current_user.is_premium:
        now = datetime.utcnow()
        # Find any redemption request by this user in the current calendar month
        monthly_request = (
            db.query(RedemptionRequest)
            .filter(
                RedemptionRequest.user_id == current_user.id,
                extract('year', RedemptionRequest.created_at) == now.year,
                extract('month', RedemptionRequest.created_at) == now.month,
            )
            .first()
        )
        if monthly_request:
            raise HTTPException(
                status_code=403,
                detail="Standard accounts are limited to one redemption per month. Upgrade to PRIME for unlimited monthly redemptions.",
            )
    # For all users: block multiple pending/approved requests
    pending_request = (
        db.query(RedemptionRequest)
        .filter(
            RedemptionRequest.user_id == current_user.id,
            RedemptionRequest.status.in_(["pending", "approved"]),
        )
        .first()
    )
    if pending_request:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending redemption request",
        )

    current_user.wallet_address = wallet_address
    db.add(current_user)

    wallet.available_points -= payload.points_requested
    db.add(wallet)


    # Calculate RSN amount (1 RSN = 1,000 points)
    rsn_amount = payload.points_requested // 1000
    request_row = RedemptionRequest(
        user_id=current_user.id,
        username_snapshot=current_user.username,
        email_snapshot=current_user.email,
        wallet_address_snapshot=wallet_address,
        points_requested=payload.points_requested,
        rsn_amount=rsn_amount,
        status="pending",
    )

    db.add(request_row)
    db.commit()
    db.refresh(request_row)

    return RedemptionRequestResponse(
        id=request_row.id,
        username_snapshot=request_row.username_snapshot,
        email_snapshot=request_row.email_snapshot,
        wallet_address_snapshot=request_row.wallet_address_snapshot,
        points_requested=request_row.points_requested,
        status=request_row.status,
        created_at=request_row.created_at.isoformat(),
        reviewed_at=request_row.reviewed_at.isoformat() if request_row.reviewed_at else None,
    )


@router.get("/redemptions", response_model=list[RedemptionRequestResponse])
def list_my_redemptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(RedemptionRequest)
        .filter(RedemptionRequest.user_id == current_user.id)
        .order_by(RedemptionRequest.created_at.desc())
        .all()
    )

    return [
        RedemptionRequestResponse(
            id=row.id,
            username_snapshot=row.username_snapshot,
            email_snapshot=row.email_snapshot,
            wallet_address_snapshot=row.wallet_address_snapshot,
            points_requested=row.points_requested,
            status=row.status,
            created_at=row.created_at.isoformat(),
            reviewed_at=row.reviewed_at.isoformat() if row.reviewed_at else None,
        )
        for row in rows
    ]


@router.get("/stats")
def get_profile_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wallet = (
        db.query(PointWallet)
        .filter(PointWallet.user_id == current_user.id)
        .first()
    )

    best_session = (
        db.query(GameSession)
        .filter(
            GameSession.user_id == current_user.id,
            GameSession.status == "finished",
        )
        .order_by(GameSession.final_score.desc(), GameSession.level_reached.desc())
        .first()
    )

    total_sessions = (
        db.query(func.count(GameSession.id))
        .filter(
            GameSession.user_id == current_user.id,
            GameSession.status == "finished",
        )
        .scalar()
    ) or 0


    # Calculate score_rank
    user_best_score = best_session.final_score if best_session else 0
    user_best_level = best_session.level_reached if best_session else 1
    # Score rank
    if user_best_score > 0:
        score_rank = (
            db.query(GameSession)
            .filter(GameSession.status == "finished")
            .filter(GameSession.final_score > user_best_score)
            .count() + 1
        )
    else:
        score_rank = None
    # Level rank
    if user_best_level > 1:
        level_rank = (
            db.query(GameSession)
            .filter(GameSession.status == "finished")
            .filter(GameSession.level_reached > user_best_level)
            .count() + 1
        )
    else:
        level_rank = None

    return {
        "username": current_user.username,
        "email": current_user.email,
        "wallet_address": current_user.wallet_address,
        "avatar_url": current_user.avatar_url,
        "generated_avatar_url": current_user.generated_avatar_url,
        "vault_trials": current_user.vault_trials or 0,
        "best_score": user_best_score,
        "best_level": user_best_level,
        "total_sessions": int(total_sessions),
        "total_points_earned": wallet.total_points_earned if wallet else 0,
        "available_points": wallet.available_points if wallet else 0,
        "claimed_points": wallet.claimed_points if wallet else 0,
        "score_rank": score_rank,
        "level_rank": level_rank,
        "is_premium": current_user.is_premium,
    }