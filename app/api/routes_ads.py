from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.db.database import get_db
from app.models.user import User
from app.api.routes_auth import get_current_user

router = APIRouter(prefix="/rush", tags=["Ads"])

MAX_DAILY_ADS = 5

@router.post("/claim-ad-reward")
def claim_ad_reward(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    today = date.today()
    # Use last_ad_date for reset
    if not user.last_ad_date or user.last_ad_date.date() != today:
        user.ads_watched_today = 0
        user.last_ad_date = datetime.utcnow()
    if user.ads_watched_today < MAX_DAILY_ADS:
        user.ads_watched_today += 1
        user.vault_trials += 1
        user.last_ad_date = datetime.utcnow()
        db.add(user)
        db.commit()
        return {"trials": user.vault_trials, "ads_watched_today": user.ads_watched_today, "limit": MAX_DAILY_ADS}
    else:
        raise HTTPException(status_code=400, detail="Ad reward limit reached for today.")
