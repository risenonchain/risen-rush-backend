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

@router.get("/debug-otp")
def debug_otp():
    """
    Temporary debug endpoint to verify server-side OTP generation.
    """
    secret = os.getenv("ADMIN_TOTP_SECRET")
    if not secret:
        return {"error": "ADMIN_TOTP_SECRET not set"}

    totp = pyotp.TOTP(secret, digits=8)
    return {
        "otp": totp.now(),
        "timestamp": int(time.time()),
        "server_time_utc": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }

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
        # NO RUNTIME ENCODING: We expect a true Base32 secret from the environment
        if not x_admin_otp:
            raise HTTPException(status_code=403, detail="Neural Sync Required.")

        # Explicitly use SHA1 and 8 digits (standard TOTP defaults to SHA1)
        import hashlib
        totp = pyotp.TOTP(TOTP_SECRET, digits=8, digest=hashlib.sha1)

        # Verify with a tighter window (1 previous/next 30s interval)
        # valid_window=2 means check current and the previous/next interval.
        if not totp.verify(x_admin_otp, valid_window=2):
            server_time = datetime.utcnow().strftime('%H:%M:%S')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Neural Sync Failed: Handshake Invalid (Server: {server_time} UTC)"
            )

        # Success! Consume code
        USED_NEURAL_CODES[x_admin_otp] = now + 90

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
