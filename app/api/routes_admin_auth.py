import os
import pyotp
import base64
import time
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import TokenResponse

router = APIRouter(prefix="/admin-auth", tags=["AdminAuth"])

# --- GLOBAL SYNC MEMORY (Replay Protection) ---
USED_NEURAL_CODES = {}

@router.post("/login", response_model=TokenResponse)
async def admin_login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    x_admin_otp: str = Header(None)
):
    # --- ULTRA-SECURE BACKEND CREDENTIALS ---
    # Clean variables (remove accidental spaces or quotes from Render)
    MASTER_ADMIN_USER = (os.getenv("MASTER_ADMIN_USERNAME") or "risen_master_admin").strip().strip('"').strip("'")
    MASTER_ADMIN_PASS = (os.getenv("MASTER_ADMIN_PASSWORD") or "").strip().strip('"').strip("'")
    TOTP_SECRET = (os.getenv("ADMIN_TOTP_SECRET") or "").strip().strip('"').strip("'")

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
    expired_codes = [code for code, expiry in USED_NEURAL_CODES.items() if expiry < now]
    for code in expired_codes:
        del USED_NEURAL_CODES[code]

    if x_admin_otp in USED_NEURAL_CODES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Neural Error: Sync Code already consumed."
        )

    try:
        secret_b32 = base64.b32encode(TOTP_SECRET.encode()).decode()

        if not x_admin_otp:
            raise HTTPException(status_code=403, detail="Neural Sync Required.")

        # --- SMART TIME-ZONE OFFSET CORRECTION ---
        # We check three windows to handle the 1-hour server drift:
        # 1. Standard (Now)
        # 2. +1 Hour (3600 seconds ahead)
        # 3. -1 Hour (3600 seconds behind)

        verified = False
        for offset in [0, 3600, -3600]:
            totp = pyotp.TOTP(secret_b32, digits=8)
            # Use a tighter window (drift=1) but shift the base time by 'offset'
            # totp.at() generates/verifies the code for a specific timestamp
            current_timestamp = int(time.time()) + offset
            if totp.verify(x_admin_otp, for_time=current_timestamp, valid_window=2):
                verified = True
                break

        if not verified:
            server_time = datetime.utcnow().strftime('%H:%M:%S')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Neural Sync Failed: Handshake Invalid (Server: {server_time} UTC)"
            )

        # Success! Consume code
        USED_NEURAL_CODES[x_admin_otp] = now + 3600 # Keep in memory longer to cover all offsets

    except HTTPException:
        raise
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Neural Engine Error: {str(e)}")

    # 3. Final handshake with DB
    user = db.query(User).filter(User.is_admin == True).first()
    if not user:
         raise HTTPException(status_code=500, detail="Neural Error: No authorized Admin node in DB.")

    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": MASTER_ADMIN_USER,
            "is_admin": True,
        }
    )
    return TokenResponse(access_token=token)
