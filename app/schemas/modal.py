from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ModalBase(BaseModel):
    title: str
    content: str
    is_active: Optional[bool] = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

class ModalCreate(ModalBase):
    pass

class ModalUpdate(ModalBase):
    pass

class ModalOut(ModalBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
