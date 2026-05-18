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


@router.get("/analytics/summary")
def get_analytics_summary(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()
    total_sessions = db.query(GameSession).count()
    premium_users = db.query(User).filter(User.is_premium == True).count()

    # Get total points in circulation
    total_points = db.query(func.sum(PointWallet.available_points)).scalar() or 0

    return {
        "total_users": total_users,
        "total_sessions": total_sessions,
        "premium_users": premium_users,
        "total_points_in_vaults": int(total_points),
    }


@router.get("/analytics/export")
def export_users_csv(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["ID", "Username", "Email", "Wallet Address", "Is Premium", "Best Score", "Best Level", "Total Points Earned", "Available Points", "Joined At"])

    for u in users:
        wallet = db.query(PointWallet).filter(PointWallet.user_id == u.id).first()
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
            u.created_at.isoformat() if hasattr(u, 'created_at') and u.created_at else ""
        ])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=risen_users_export.csv"}
    )
