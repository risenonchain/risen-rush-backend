import os
import pyotp
import base64
import time
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/admin-auth", tags=["AdminAuth"])

# --- GLOBAL SYNC MEMORY (Replay Protection) ---
# Stores used OTPs to prevent reuse within their valid window.
# Format: { "otp_code": expiry_timestamp }
USED_NEURAL_CODES = {}

@router.post("/login", response_model=TokenResponse)
async def admin_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_admin_otp: str = Header(None)
):
    # --- ULTRA-SECURE BACKEND CREDENTIALS ---
    MASTER_ADMIN_USER = os.getenv("MASTER_ADMIN_USERNAME", "risen_master_admin")
    MASTER_ADMIN_PASS = os.getenv("MASTER_ADMIN_PASSWORD")
    TOTP_SECRET = os.getenv("ADMIN_TOTP_SECRET")

    # 1. Credentials Check
    if not MASTER_ADMIN_PASS:
         raise HTTPException(status_code=500, detail="Neural Error: Admin Passkey not defined.")

    if form_data.username != MASTER_ADMIN_USER or form_data.password != MASTER_ADMIN_PASS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Neural Access Denied: Credentials Mismatch",
        )

    # 2. Neural Sync (8-Digit TOTP) Check
    if not TOTP_SECRET:
        raise HTTPException(status_code=500, detail="Neural Error: Sync Secret not defined.")

    # --- REPLAY PROTECTION ---
    now = time.time()
    # Clean up old codes from memory
    expired_codes = [code for code, expiry in USED_NEURAL_CODES.items() if expiry < now]
    for code in expired_codes:
        del USED_NEURAL_CODES[code]

    if x_admin_otp in USED_NEURAL_CODES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Neural Error: Sync Code already consumed. Generate a fresh one."
        )

    try:
        secret_b32 = base64.b32encode(TOTP_SECRET.encode()).decode()
        totp = pyotp.TOTP(secret_b32, digits=8)

        if not x_admin_otp:
            raise HTTPException(status_code=403, detail="Neural Sync Required.")

        # Allow 60 seconds of time drift (valid_window=2)
        if not totp.verify(x_admin_otp, valid_window=2):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Neural Sync Failed: Handshake Invalid"
            )

        # Success! Consume the code so it can't be used again for 2 minutes
        USED_NEURAL_CODES[x_admin_otp] = now + 120

    except HTTPException:
        raise
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Neural Engine Sync Error: {str(e)}")

    # 3. Find a real Admin in DB to attach the session token permissions
    # This prevents mixing up with the 'admin' player by checking for is_admin=True
    user = db.query(User).filter(User.is_admin == True).first()
    if not user:
         raise HTTPException(status_code=500, detail="Neural Error: No authorized Admin node found in DB.")

    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": MASTER_ADMIN_USER,
            "is_admin": True,
        }
    )
    return TokenResponse(access_token=token)
