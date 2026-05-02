from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date
from app.db.database import get_db
from app.models.user import User
from app.api.routes_auth import get_current_user

router = APIRouter(prefix="/rush", tags=["Ads"])

MAX_DAILY_ADS = 5


import logging

@router.post("/claim-ad-reward")
def claim_ad_reward(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    logger = logging.getLogger("ads")
    today = date.today()
    logger.info(f"Ad reward attempt: user={user.id}, today={today}, last_ad_date={user.last_ad_date}, ads_watched_today={user.ads_watched_today}, vault_trials={user.vault_trials}")
    try:
        # Use last_ad_date for reset
        if not user.last_ad_date or user.last_ad_date.date() != today:
            logger.info(f"Resetting ads_watched_today for user={user.id}")
            user.ads_watched_today = 0
            user.last_ad_date = datetime.utcnow()
        if user.ads_watched_today < MAX_DAILY_ADS:
            user.ads_watched_today += 1
            user.vault_trials += 1
            user.last_ad_date = datetime.utcnow()
            db.add(user)
            db.commit()
            logger.info(f"Ad reward granted: user={user.id}, ads_watched_today={user.ads_watched_today}, vault_trials={user.vault_trials}")
            return {"trials": user.vault_trials, "ads_watched_today": user.ads_watched_today, "limit": MAX_DAILY_ADS}
        else:
            logger.warning(f"Ad reward denied (limit reached): user={user.id}, ads_watched_today={user.ads_watched_today}")
            raise HTTPException(status_code=400, detail="Ad reward limit reached for today.")
    except Exception as e:
        logger.error(f"Ad reward error for user={user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during ad reward.")
