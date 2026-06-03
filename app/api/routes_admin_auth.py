import os
import pyotp
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/admin-auth", tags=["AdminAuth"])

@router.post("/login", response_model=TokenResponse)
async def admin_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_admin_otp: str = Header(None)
):
    # --- ULTRA-SECURE BACKEND CREDENTIALS ---
    # These values are pulled directly from Render Environment, bypassing the DB
    MASTER_ADMIN_USER = os.getenv("MASTER_ADMIN_USERNAME", "admin")
    MASTER_ADMIN_PASS = os.getenv("MASTER_ADMIN_PASSWORD")
    TOTP_SECRET = os.getenv("ADMIN_TOTP_SECRET")

    # 1. Check Username and Password against Backend Env
    if form_data.username != MASTER_ADMIN_USER or form_data.password != MASTER_ADMIN_PASS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neural Access Denied: Core Credentials Mismatch",
        )

    # 2. Neural Sync (8-Digit TOTP) Check
    if not TOTP_SECRET:
        print("CRITICAL: ADMIN_TOTP_SECRET not found in environment!")
    else:
        import base64
        # Match the user's local complex secret generation logic
        secret_b32 = base64.b32encode(TOTP_SECRET.encode()).decode()
        totp = pyotp.TOTP(secret_b32, digits=8)
        if not x_admin_otp or not totp.verify(x_admin_otp):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Neural Sync Failed: Handshake Invalid"
            )

    # 3. Fetch the 'admin' user from DB just to get a valid ID for the token
    # We still need a valid user ID for subsequent permission checks
    user = db.query(User).filter(User.username == MASTER_ADMIN_USER, User.is_admin == True).first()
    if not user:
        # Fallback to the first admin found if 'admin' username doesn't match DB entry
        user = db.query(User).filter(User.is_admin == True).first()

    if not user:
         raise HTTPException(status_code=500, detail="Database Error: No Admin node found to attach session.")

    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "is_admin": True,
        }
    )
    return TokenResponse(access_token=token)
