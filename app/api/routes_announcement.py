from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.announcement import Announcement
from app.schemas.announcement import AnnouncementCreate, AnnouncementOut
from app.api.routes_admin import require_admin
from app.models.user import User

router = APIRouter(prefix="/announcements", tags=["Announcements"])

@router.get("/active", response_model=AnnouncementOut | None)
def get_active_announcement(db: Session = Depends(get_db)):
    return db.query(Announcement).filter(Announcement.is_active == True).order_by(Announcement.created_at.desc()).first()

@router.post("/", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def push_announcement(
    payload: AnnouncementCreate,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # Archive previous announcements
    db.query(Announcement).filter(Announcement.is_active == True).update({"is_active": False})

    new_announcement = Announcement(message=payload.message, is_active=True)
    db.add(new_announcement)
    db.commit()
    db.refresh(new_announcement)
    return new_announcement
