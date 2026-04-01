from pydantic import BaseModel, Field


class AdminRedemptionStatusUpdate(BaseModel):
    status: str = Field(min_length=4, max_length=20)