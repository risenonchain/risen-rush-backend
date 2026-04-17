from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.modal import ModalCreate, ModalUpdate, ModalOut
from app.services.modal_service import (
    get_modals, get_modal_by_id, create_modal, update_modal, delete_modal
)

router = APIRouter(prefix="/modals", tags=["modals"])

@router.get("/", response_model=List[ModalOut])
def list_modals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_modals(db, skip=skip, limit=limit)

@router.get("/{modal_id}", response_model=ModalOut)
def read_modal(modal_id: int, db: Session = Depends(get_db)):
    modal = get_modal_by_id(db, modal_id)
    if not modal:
        raise HTTPException(status_code=404, detail="Modal not found")
    return modal

@router.post("/", response_model=ModalOut, status_code=status.HTTP_201_CREATED)
def create_modal_item(modal: ModalCreate, db: Session = Depends(get_db)):
    return create_modal(db, modal)

@router.put("/{modal_id}", response_model=ModalOut)
def update_modal_item(modal_id: int, modal: ModalUpdate, db: Session = Depends(get_db)):
    updated = update_modal(db, modal_id, modal)
    if not updated:
        raise HTTPException(status_code=404, detail="Modal not found")
    return updated

@router.delete("/{modal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_modal_item(modal_id: int, db: Session = Depends(get_db)):
    deleted = delete_modal(db, modal_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Modal not found")
    return None
