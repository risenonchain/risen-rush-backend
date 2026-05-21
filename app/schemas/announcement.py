from datetime import datetime
from pydantic import BaseModel

class AnnouncementBase(BaseModel):
    message: str

class AnnouncementCreate(AnnouncementBase):
    pass

class AnnouncementOut(AnnouncementBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
