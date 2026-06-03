from datetime import datetime
import io
import csv

from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.routes_auth import get_current_user
from app.db.database import get_db
from app.models.redemption_request import RedemptionRequest
from app.models.user import User
from app.models.game_session import GameSession
from app.models.season import Season
from app.models.point_wallet import PointWallet
from app.services.subscription_service import cleanup_expired_prime_users

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/redemptions")
def list_redemption_requests(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(RedemptionRequest)
        .order_by(RedemptionRequest.created_at.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "username": row.username_snapshot,
            "email": row.email_snapshot,
            "wallet_address": row.wallet_address_snapshot,
            "points_requested": row.points_requested,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
            "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        }
        for row in rows
    ]


@router.patch("/redemptions/{request_id}")
def update_redemption_request_status(
    request_id: int,
    status: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    allowed_statuses = {"pending", "approved", "paid", "rejected"}
    next_status = status.strip().lower()

    if next_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid redemption status")

    row = (
        db.query(RedemptionRequest)
        .filter(RedemptionRequest.id == request_id)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Redemption request not found")

    row.status = next_status
    row.reviewed_by_user_id = current_admin.id
    row.reviewed_at = datetime.utcnow()

    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "message": "Redemption request updated",
        "request_id": row.id,
        "status": row.status,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }


@router.post("/seasons/reset")
def reset_season(
    name: str = Body(..., embed=True),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Deactivate current active seasons
    db.query(Season).filter(Season.is_active == True).update({"is_active": False, "end_at": datetime.utcnow()})

    # Create new season
    new_season = Season(name=name, is_active=True, start_at=datetime.utcnow())
    db.add(new_season)
    db.commit()
    db.refresh(new_season)

    return {"message": f"Season '{name}' started", "season_id": new_season.id}


@router.post("/leaderboard/hard-reset")
def hard_reset_leaderboard(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # 1. Delete all non-league game sessions
    db.query(GameSession).filter(GameSession.is_league_game == False).delete()

    # 2. Reset user best scores/levels
    db.query(User).update({User.best_score: 0, User.best_level: 1})

    # 3. Start a fresh season to ensure start_at is NOW
    db.query(Season).filter(Season.is_active == True).update({"is_active": False, "end_at": datetime.utcnow()})
    new_season = Season(
        name="Hard Reset " + datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        is_active=True,
        start_at=datetime.utcnow()
    )
    db.add(new_season)

    db.commit()
    return {"message": "Leaderboard wiped clean and personal bests reset."}


@router.get("/analytics/summary")
def get_analytics_summary(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()
    total_sessions = db.query(GameSession).count()
    premium_users = db.query(User).filter(User.is_premium == True).count()

    today = datetime.utcnow().date()
    users_today = db.query(User).filter(func.date(User.created_at) == today).count()
    sessions_today = db.query(GameSession).filter(func.date(GameSession.started_at) == today).count()

    # Get active season
    active_season = db.query(Season).filter(Season.is_active == True).first()

    # Get total points in circulation
    total_points = db.query(func.sum(PointWallet.available_points)).scalar() or 0

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "premium_users": premium_users,
        "total_points_in_vaults": int(total_points),
        "users_today": users_today,
        "sessions_today": sessions_today,
        "active_season": {
            "name": active_season.name if active_season else "None",
            "start_at": active_season.start_at.isoformat() if active_season else None
        }
    }


@router.get("/analytics/users")
def get_detailed_users(
    search: str | None = None,
    sort_by: str = "id",
    order: str = "desc",
    is_premium: bool | None = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User, PointWallet).join(PointWallet, User.id == PointWallet.user_id)

    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    if is_premium is not None:
        query = query.filter(User.is_premium == is_premium)

    # Sorting logic
    sort_attr = getattr(User, sort_by, None)
    if not sort_attr:
        # Check PointWallet for sorting (e.g., points)
        if sort_by == "available_points":
            sort_attr = PointWallet.available_points
        elif sort_by == "total_points_earned":
            sort_attr = PointWallet.total_points_earned
        else:
            sort_attr = User.id

    if order == "desc":
        query = query.order_by(sort_attr.desc())
    else:
        query = query.order_by(sort_attr.asc())

    results = query.limit(100).all()

    today = datetime.utcnow().date()

    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_premium": u.is_premium,
            "best_score": u.best_score,
            "best_level": u.best_level,
            "available_points": w.available_points,
            "total_points_earned": w.total_points_earned,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "is_today": u.created_at.date() == today if u.created_at else False,
        }
        for u, w in results
    ]


@router.get("/analytics/export")
def export_users_csv(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    today = datetime.utcnow().date()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "ID", "Username", "Email", "Wallet Address", "Is Premium",
        "Best Score", "Best Level", "Total Points Earned", "Available Points",
        "Joined At", "Registered Today", "Sessions Today"
    ])

    for u in users:
        wallet = db.query(PointWallet).filter(PointWallet.user_id == u.id).first()

        # Check if registered today
        is_today = u.created_at.date() == today if hasattr(u, 'created_at') and u.created_at else False

        # Count sessions today
        sessions_today = db.query(GameSession).filter(
            GameSession.user_id == u.id,
            func.date(GameSession.started_at) == today
        ).count()

        writer.writerow([
            u.id,
            u.username,
            u.email,
            u.wallet_address or "",
            u.is_premium,
            u.best_score,
            u.best_level,
            wallet.total_points_earned if wallet else 0,
            wallet.available_points if wallet else 0,
            u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else "",
            "YES" if is_today else "NO",
            sessions_today
        ])

    output.seek(0)

    filename = f"risen_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/prime/cleanup")
def trigger_prime_cleanup(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Manually trigger the cleanup of expired Prime users who passed the grace period.
    """
    reverted_count = cleanup_expired_prime_users(db)
    return {"message": f"Cleanup successful. {reverted_count} users reverted to standard."}


@router.post("/prime/grant/{user_id}")
def grant_prime_access(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Grant 30 days of Prime access to a specific user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_premium = True
    user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
    db.add(user)
    db.commit()

    return {"message": f"Prime access granted to {user.username} until {user.premium_expires_at.isoformat()}"}
