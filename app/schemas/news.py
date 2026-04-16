from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NewsBase(BaseModel):
    title: str
    summary: str
    details: str
    url: Optional[str] = None
    is_active: Optional[bool] = True

class NewsCreate(NewsBase):
    pass

class NewsUpdate(NewsBase):
    pass

class NewsOut(NewsBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
