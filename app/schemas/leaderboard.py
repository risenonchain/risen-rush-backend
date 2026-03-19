from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    score: int
    level: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]