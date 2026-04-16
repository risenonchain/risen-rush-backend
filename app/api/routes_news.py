from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.news import NewsCreate, NewsUpdate, NewsOut
from app.services.news_service import (
    get_news, get_news_by_id, create_news, update_news, delete_news
)

router = APIRouter(prefix="/news", tags=["news"])

@router.get("/", response_model=List[NewsOut])
def list_news(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_news(db, skip=skip, limit=limit)

@router.get("/{news_id}", response_model=NewsOut)
def read_news(news_id: int, db: Session = Depends(get_db)):
    news = get_news_by_id(db, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news

@router.post("/", response_model=NewsOut, status_code=status.HTTP_201_CREATED)
def create_news_item(news: NewsCreate, db: Session = Depends(get_db)):
    return create_news(db, news)

@router.put("/{news_id}", response_model=NewsOut)
def update_news_item(news_id: int, news: NewsUpdate, db: Session = Depends(get_db)):
    updated = update_news(db, news_id, news)
    if not updated:
        raise HTTPException(status_code=404, detail="News not found")
    return updated

@router.delete("/{news_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news_item(news_id: int, db: Session = Depends(get_db)):
    deleted = delete_news(db, news_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="News not found")
    return None
