from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.game_session import GameSession
from app.models.user import User
from app.models.season import Season

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

LEADERBOARD_LIMIT = 20

def get_active_season_start(db: Session):
    active_season = db.query(Season).filter(Season.is_active == True).first()
    return active_season.start_at if active_season else None

@router.get("/top-score")
def get_top_score_leaderboard(db: Session = Depends(get_db)):
    start_at = get_active_season_start(db)
    query = (
        db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            func.max(GameSession.final_score).label("score"),
            func.max(GameSession.level_reached).label("level"),
        )
        .join(GameSession, GameSession.user_id == User.id)
        .filter(
            GameSession.status == "finished",
            GameSession.final_score.isnot(None),
            GameSession.is_league_game == False,
        )
    )

    if start_at:
        query = query.filter(GameSession.ended_at >= start_at)

    results = (
        query.group_by(User.id, User.username)
        .order_by(
            func.max(GameSession.final_score).desc(),
            func.max(GameSession.level_reached).desc(),
            User.username.asc(),
        )
        .limit(LEADERBOARD_LIMIT)
        .all()
    )

    # Fetch is_premium for each user
    user_ids = [row.user_id for row in results]
    premium_map = {u.id: u.is_premium for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    return [
        {
            "rank": index,
            "username": row.username,
            "score": int(row.score or 0),
            "level": int(row.level or 1),
            "is_premium": premium_map.get(row.user_id, False),
        }
        for index, row in enumerate(results, start=1)
    ]


@router.get("/top-level")
def get_top_level_leaderboard(db: Session = Depends(get_db)):
    start_at = get_active_season_start(db)
    query = (
        db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            func.max(GameSession.final_score).label("score"),
            func.max(GameSession.level_reached).label("level"),
        )
        .join(GameSession, GameSession.user_id == User.id)
        .filter(
            GameSession.status == "finished",
            GameSession.level_reached.isnot(None),
            GameSession.is_league_game == False,
        )
    )

    if start_at:
        query = query.filter(GameSession.ended_at >= start_at)

    results = (
        query.group_by(User.id, User.username)
        .order_by(
            func.max(GameSession.level_reached).desc(),
            func.max(GameSession.final_score).desc(),
            User.username.asc(),
        )
        .limit(LEADERBOARD_LIMIT)
        .all()
    )

    user_ids = [row.user_id for row in results]
    premium_map = {u.id: u.is_premium for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    return [
        {
            "rank": index,
            "username": row.username,
            "score": int(row.score or 0),
            "level": int(row.level or 1),
            "is_premium": premium_map.get(row.user_id, False),
        }
        for index, row in enumerate(results, start=1)
    ]


@router.get("/global")
def get_global_leaderboard(db: Session = Depends(get_db)):
    # Backward-compatible alias to top-score leaderboard
    return get_top_score_leaderboard(db)