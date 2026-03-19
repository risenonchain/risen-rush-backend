from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.models.user import User
from app.models.game_session import GameSession

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("/global")
def get_global_leaderboard(db: Session = Depends(get_db)):
    """
    Return top 50 players ranked by highest recorded finished Rush score.

    Flat array response shape:
    [
      {
        "rank": 1,
        "username": "player1",
        "score": 120,
        "level": 3
      }
    ]
    """

    results = (
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
        )
        .group_by(User.id, User.username)
        .order_by(
            func.max(GameSession.final_score).desc(),
            func.max(GameSession.level_reached).desc(),
            User.username.asc(),
        )
        .limit(50)
        .all()
    )

    leaderboard = [
        {
            "rank": index,
            "username": row.username,
            "score": int(row.score or 0),
            "level": int(row.level or 1),
        }
        for index, row in enumerate(results, start=1)
    ]

    return leaderboard