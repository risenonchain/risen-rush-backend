from pydantic import BaseModel

class GuardianStatsResponse(BaseModel):
    total_scans: int
    active_alerts: int
    monitored_assets: int
    safety_score: str
