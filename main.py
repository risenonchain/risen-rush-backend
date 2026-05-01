from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes_auth import router as auth_router
from app.api.routes_game import router as rush_router
from app.api.routes_leaderboard import router as leaderboard_router
from app.api.routes_profile import router as profile_router
from app.api.routes_admin import router as admin_router
from app.api.routes_admin_auth import router as admin_auth_router
from app.api.routes_news import router as news_router
from app.api.routes_modal import router as modal_router
from app.api.routes_ads import router as ads_router
from app.api.routes_payments import router as payments_router
from app.db.database import Base, engine

from app.models.user import User  # noqa
from app.models.daily_trial import DailyTrial  # noqa
from app.models.game_session import GameSession  # noqa
from app.models.point_wallet import PointWallet  # noqa
from app.models.referral_reward import ReferralReward  # noqa
#from app.models.user_device import UserDevice  # noqa
from app.models.redemption_request import RedemptionRequest  # noqa

print("DATABASE_URL IN USE:", settings.database_url)



from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import re

# --- Ensure app is defined before middleware ---
app = FastAPI()

MIN_APP_VERSION = "1.1.0"

def parse_version(version_str):
    # Accepts '1.2.3', '1.2', etc.
    return tuple(int(x) for x in re.split(r'\.|-', version_str) if x.isdigit())

def is_version_outdated(client_version, min_version):
    try:
        client_tuple = parse_version(client_version)
        min_tuple = parse_version(min_version)
        return client_tuple < min_tuple
    except Exception:
        return False  # If parsing fails, allow


class VersionCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only check for API routes, skip docs/static
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi"):
            return await call_next(request)
        version = request.headers.get("X-App-Version")
        if version and is_version_outdated(version, MIN_APP_VERSION):
            return JSONResponse(
                status_code=403,
                content={"detail": "Update Required: Please download the latest version."},
            )
        return await call_next(request)


app.add_middleware(VersionCheckMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://app.risenonchain.net",
        "https://risenonchain.net",
        "https://www.risenonchain.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(rush_router)
app.include_router(leaderboard_router)
app.include_router(profile_router)
app.include_router(admin_router)

app.include_router(news_router)
app.include_router(admin_auth_router)
app.include_router(modal_router)
app.include_router(ads_router)
app.include_router(payments_router)


@app.get("/")
def root():
    return {"message": "RISEN Rush API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}