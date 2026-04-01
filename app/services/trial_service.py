from datetime import date

from sqlalchemy.orm import Session

from app.models.daily_trial import DailyTrial
from app.models.user import User


MAX_DAILY_TRIALS = 3


def get_or_create_today_trial(user_id: int, db: Session) -> DailyTrial:
    today = date.today()

    trial = (
        db.query(DailyTrial)
        .filter(DailyTrial.user_id == user_id, DailyTrial.date == today)
        .first()
    )

    if not trial:
        trial = DailyTrial(user_id=user_id, date=today)
        db.add(trial)
        db.commit()
        db.refresh(trial)

    return trial


def get_daily_trials_remaining(user_id: int, db: Session) -> int:
    trial = get_or_create_today_trial(user_id, db)
    max_trials = MAX_DAILY_TRIALS + trial.extra_trials_purchased
    remaining = max_trials - trial.trials_used
    return max(remaining, 0)


def get_vault_trials_remaining(user_id: int, db: Session) -> int:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return 0
    return max(user.vault_trials or 0, 0)


def get_remaining_trials(user_id: int, db: Session) -> int:
    daily_remaining = get_daily_trials_remaining(user_id, db)
    vault_remaining = get_vault_trials_remaining(user_id, db)
    return daily_remaining + vault_remaining


def consume_trial(user_id: int, db: Session) -> tuple[bool, str | None]:
    trial = get_or_create_today_trial(user_id, db)
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return False, None

    max_daily_trials = MAX_DAILY_TRIALS + trial.extra_trials_purchased

    if trial.trials_used < max_daily_trials:
        trial.trials_used += 1
        db.commit()
        return True, "daily"

    if (user.vault_trials or 0) > 0:
        user.vault_trials -= 1
        db.add(user)
        db.commit()
        return True, "vault"

    return False, None