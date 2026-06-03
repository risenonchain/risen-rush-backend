from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.user import User

def cleanup_expired_prime_users(db: Session):
    """
    Reverts users to standard status if they are 3 days past their expiration date.
    """
    now = datetime.utcnow()
    grace_period_end = now - timedelta(days=3)

    # Identify users who are past the 3-day grace period
    expired_users = db.query(User).filter(
        User.is_premium == True,
        User.premium_expires_at < grace_period_end
    ).all()

    count = 0
    for user in expired_users:
        user.is_premium = False
        db.add(user)
        count += 1

    if count > 0:
        db.commit()

    return count

def check_and_update_user_subscription(db: Session, user: User) -> bool:
    """
    Checks a single user's subscription and updates it if past the grace period.
    Returns True if the user is still premium (within grace period or not expired).
    """
    if not user.is_premium:
        return False

    if not user.premium_expires_at:
        # If somehow they are premium but have no expiry, we leave them be or set one?
        # For safety, let's assume they are fine but log it or something.
        return True

    now = datetime.utcnow()
    grace_limit = user.premium_expires_at + timedelta(days=3)

    if now > grace_limit:
        user.is_premium = False
        db.add(user)
        db.commit()
        db.refresh(user)
        return False

    return True
