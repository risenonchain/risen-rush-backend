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
    Return top 50 players ranked by highest recorded Rush score.
    Response shape matches frontend LeaderboardEntry:
    {
      rank: number,
      username: string,
      score: number,
      level: number
    }
    """

    results = (
        db.query(
            User.id.label("user_id"),
            User.username.label("username"),
            User.level.label("level"),
            func.max(GameSession.final_score).label("score"),
        )
        .join(GameSession, GameSession.user_id == User.id)
        .filter(
            GameSession.status == "finished",
            GameSession.final_score.isnot(None),
        )
        .group_by(User.id, User.username, User.level)
        .order_by(func.max(GameSession.final_score).desc(), User.username.asc())
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