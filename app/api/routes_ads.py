from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.db.database import get_db
from app.models.user import User
from app.api.routes_auth import get_current_user

router = APIRouter(prefix="/rush", tags=["Ads"])

@router.post("/claim-ad-reward")
def claim_ad_reward(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    today = date.today()
    if not user.last_ad_reward_at or user.last_ad_reward_at.date() != today:
        user.ads_watched_today = 0
    if user.ads_watched_today < 2:
        user.ads_watched_today += 1
        user.vault_trials += 1
        user.last_ad_reward_at = datetime.utcnow()
        db.add(user)
        db.commit()
        return {"trials": user.vault_trials}
    else:
        raise HTTPException(status_code=400, detail="Ad reward limit reached for today.")
