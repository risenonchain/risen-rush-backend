from datetime import datetime
from secrets import token_urlsafe

import requests
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_access_token,
    get_password_hash,
    get_password_reset_expiry,
    pwd_context,
    verify_password,
)
from app.db.database import get_db
from app.models.point_wallet import PointWallet
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def generate_referral_code() -> str:
    return token_urlsafe(6).replace("-", "").replace("_", "").upper()


def generate_unique_referral_code(db: Session) -> str:
    while True:
        code = generate_referral_code()
        existing = db.query(User).filter(User.referral_code == code).first()
        if not existing:
            return code


def get_request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def verify_turnstile_or_raise(request: Request, action: str) -> None:
    if not settings.turnstile_enabled:
        return

    token = request.headers.get("X-Turnstile-Token")
    if not token:
        raise HTTPException(
            status_code=400,
            detail=f"Turnstile verification is required for {action}",
        )

    remoteip = get_request_ip(request)

    try:
        response = requests.post(
            TURNSTILE_VERIFY_URL,
            data={
                "secret": settings.turnstile_secret_key,
                "response": token,
                "remoteip": remoteip,
            },
            timeout=10,
        )
        result = response.json()
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Turnstile verification service is unavailable",
        )

    if not result.get("success", False):
        raise HTTPException(
            status_code=400,
            detail="Turnstile verification failed",
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    verify_turnstile_or_raise(request, "registration")

    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_username = db.query(User).filter(User.username == payload.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")

    referred_by_user_id = None
    if payload.referral_code:
        referrer = (
            db.query(User)
            .filter(User.referral_code == payload.referral_code.strip().upper())
            .first()
        )
        if not referrer:
            raise HTTPException(status_code=400, detail="Invalid referral code")
        referred_by_user_id = referrer.id

    try:
        new_user = User(
            email=payload.email,
            username=payload.username,
            password_hash=get_password_hash(payload.password),
            referral_code=generate_unique_referral_code(db),
            referred_by_user_id=referred_by_user_id,
            vault_trials=0,
            is_admin=False,
        )
        db.add(new_user)
        db.flush()

        wallet = PointWallet(
            user_id=new_user.id,
            total_points_earned=0,
            available_points=0,
            claimed_points=0,
        )
        db.add(wallet)

        db.commit()
        db.refresh(new_user)
        return new_user

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=(
                f"Registration failed | scheme={pwd_context.schemes()} | "
                f"type={type(e).__name__} | error={str(e)}"
            ),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    verify_turnstile_or_raise(request, "login")

    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "is_admin": user.is_admin,
        }
    )

    return TokenResponse(access_token=token)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="No account found with that email")

    try:
        reset_token = create_password_reset_token()
        expires_at = get_password_reset_expiry()

        user.reset_token = reset_token
        user.reset_token_expires_at = expires_at

        db.add(user)
        db.commit()

        return ForgotPasswordResponse(
            message="Reset token generated successfully.",
            reset_token=reset_token,
            expires_at=expires_at.isoformat(),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate reset token: {type(e).__name__} | {str(e)}",
        )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == payload.token).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid reset token")

    if not user.reset_token_expires_at or user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    try:
        user.password_hash = get_password_hash(payload.new_password)
        user.reset_token = None
        user.reset_token_expires_at = None

        db.add(user)
        db.commit()

        return MessageResponse(message="Password reset successful")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset password: {type(e).__name__} | {str(e)}",
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user