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
    # Search by username OR email for flexibility
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username),
        User.is_admin == True
    ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials",
        )

    # --- Neural Sync (8-Digit TOTP) Check ---
    secret = os.getenv("ADMIN_TOTP_SECRET")
    if not secret:
        # Emergency log if secret is missing in environment
        print("CRITICAL: ADMIN_TOTP_SECRET not found in environment!")
    else:
        totp = pyotp.TOTP(secret, digits=8)
        if not x_admin_otp or not totp.verify(x_admin_otp):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Neural Sync Failed: Invalid or missing 8-digit OTP"
            )

    token = create_access_token(
        data={
            "sub": str(user.id),
            "username": user.username,
            "is_admin": user.is_admin,
        }
    )
    return TokenResponse(access_token=token)
