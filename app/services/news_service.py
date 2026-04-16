from sqlalchemy.orm import Session
from app.models.news import News
from app.schemas.news import NewsCreate, NewsUpdate
from typing import List, Optional

def get_news(db: Session, skip: int = 0, limit: int = 100) -> List[News]:
    return db.query(News).order_by(News.created_at.desc()).offset(skip).limit(limit).all()

def get_news_by_id(db: Session, news_id: int) -> Optional[News]:
    return db.query(News).filter(News.id == news_id).first()

def create_news(db: Session, news: NewsCreate) -> News:
    db_news = News(**news.dict())
    db.add(db_news)
    db.commit()
    db.refresh(db_news)
    return db_news

def update_news(db: Session, news_id: int, news: NewsUpdate) -> Optional[News]:
    db_news = get_news_by_id(db, news_id)
    if not db_news:
        return None
    for field, value in news.dict(exclude_unset=True).items():
        setattr(db_news, field, value)
    db.commit()
    db.refresh(db_news)
    return db_news

def delete_news(db: Session, news_id: int) -> bool:
    db_news = get_news_by_id(db, news_id)
    if not db_news:
        return False
    db.delete(db_news)
    db.commit()
    return True
