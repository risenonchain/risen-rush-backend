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
    # These values are pulled directly from Render Environment
    MASTER_ADMIN_USER = os.getenv("MASTER_ADMIN_USERNAME", "risen_master_admin")
    MASTER_ADMIN_PASS = os.getenv("MASTER_ADMIN_PASSWORD")
    TOTP_SECRET = os.getenv("ADMIN_TOTP_SECRET")

    # 1. Check Username and Password against Backend Env
    if not MASTER_ADMIN_PASS:
         raise HTTPException(status_code=500, detail="Neural Error: Admin Passkey not defined in backend.")

    if form_data.username != MASTER_ADMIN_USER or form_data.password != MASTER_ADMIN_PASS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neural Access Denied: Core Credentials Mismatch",
        )

    # 2. Neural Sync (8-Digit TOTP) Check
    if not TOTP_SECRET:
        raise HTTPException(status_code=500, detail="Neural Error: Sync Secret not defined in backend.")

    import base64
    import pyotp
    try:
        # Match the user's local complex secret generation logic
        secret_b32 = base64.b32encode(TOTP_SECRET.encode()).decode()
        totp = pyotp.TOTP(secret_b32, digits=8)

        if not x_admin_otp:
            raise HTTPException(status_code=403, detail="Neural Sync Required: Please enter your 8-digit code.")

        if not totp.verify(x_admin_otp):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Neural Sync Failed: Handshake Invalid"
            )
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Neural Engine Sync Error: {str(e)}")

    # 3. Use a hardcoded dummy ID for the token to avoid mixing with 'admin' player
    # The 'sub' in the token just needs to be a string. We use '999999' as a Reserved Admin ID.
    token = create_access_token(
        data={
            "sub": "999999",
            "username": MASTER_ADMIN_USER,
            "is_admin": True,
        }
    )
    return TokenResponse(access_token=token)
