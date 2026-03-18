from pydantic import BaseModel


class StartSessionResponse(BaseModel):
    session_id: int
    session_token: str
    trials_remaining: int
    starting_lives: int = 3


class FinishSessionRequest(BaseModel):
    session_id: int
    final_score: int
    duration_seconds: int
    level_reached: int
    lives_remaining: int


class WalletResponse(BaseModel):
    total_points_earned: int
    available_points: int
    claimed_points: int


