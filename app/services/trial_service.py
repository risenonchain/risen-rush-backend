from datetime import date

from sqlalchemy.orm import Session

from app.models.daily_trial import DailyTrial


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


def get_remaining_trials(user_id: int, db: Session) -> int:
    trial = get_or_create_today_trial(user_id, db)

    max_trials = MAX_DAILY_TRIALS + trial.extra_trials_purchased
    remaining = max_trials - trial.trials_used

    return max(remaining, 0)


def consume_trial(user_id: int, db: Session):
    trial = get_or_create_today_trial(user_id, db)

    max_trials = MAX_DAILY_TRIALS + trial.extra_trials_purchased

    if trial.trials_used >= max_trials:
        return False

    trial.trials_used += 1
    db.commit()

    return True