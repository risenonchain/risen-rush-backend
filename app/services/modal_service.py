from sqlalchemy.orm import Session
from app.models.modal import Modal
from app.schemas.modal import ModalCreate, ModalUpdate
from typing import List, Optional

def get_modals(db: Session, skip: int = 0, limit: int = 100) -> List[Modal]:
    return db.query(Modal).order_by(Modal.created_at.desc()).offset(skip).limit(limit).all()

def get_modal_by_id(db: Session, modal_id: int) -> Optional[Modal]:
    return db.query(Modal).filter(Modal.id == modal_id).first()

def create_modal(db: Session, modal: ModalCreate) -> Modal:
    db_modal = Modal(**modal.dict())
    db.add(db_modal)
    db.commit()
    db.refresh(db_modal)
    return db_modal

def update_modal(db: Session, modal_id: int, modal: ModalUpdate) -> Optional[Modal]:
    db_modal = get_modal_by_id(db, modal_id)
    if not db_modal:
        return None
    for field, value in modal.dict(exclude_unset=True).items():
        setattr(db_modal, field, value)
    db.commit()
    db.refresh(db_modal)
    return db_modal

def delete_modal(db: Session, modal_id: int) -> bool:
    db_modal = get_modal_by_id(db, modal_id)
    if not db_modal:
        return False
    db.delete(db_modal)
    db.commit()
    return True
