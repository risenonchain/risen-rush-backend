from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_game import router as rush_router
from app.api.routes_leaderboard import router as leaderboard_router

from app.db.database import Base, engine

# Import models BEFORE create_all
from app.models.user import User  # noqa
from app.models.daily_trial import DailyTrial  # noqa
from app.models.game_session import GameSession  # noqa
from app.models.point_wallet import PointWallet  # noqa

app = FastAPI(title="RISEN Rush API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://risenonchain.net",
        "https://www.risenonchain.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ CREATE TABLES IN POSTGRES
Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(rush_router)
app.include_router(leaderboard_router)


@app.get("/")
def root():
    return {
        "message": "RISEN Rush API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}