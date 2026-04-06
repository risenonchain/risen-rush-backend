from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    pass


class StartSessionResponse(BaseModel):
    session_id: int
    session_token: str
    trials_remaining: int
    daily_trials_remaining: int = 0
    vault_trials_remaining: int = 0
    starting_lives: int = 3
    trial_source: str | None = None


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
    vault_trials: int = 0


class ReferralInfoResponse(BaseModel):
    referral_code: str
    referral_link: str
    vault_trials: int
    successful_referrals: int


class RedemptionRequestCreate(BaseModel):
    wallet_address: str = Field(min_length=6, max_length=255)
    points_requested: int = Field(gt=0)


class RedemptionRequestResponse(BaseModel):
    id: int
    username_snapshot: str
    email_snapshot: str
    wallet_address_snapshot: str
    points_requested: int
    status: str
    created_at: str
    reviewed_at: str | None = None
