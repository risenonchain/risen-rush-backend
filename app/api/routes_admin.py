from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes_auth import get_current_user
from app.db.database import get_db
from app.models.redemption_request import RedemptionRequest
from app.models.user import User

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