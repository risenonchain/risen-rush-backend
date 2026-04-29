

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.user import User
from app.api.routes_auth import get_current_user
from pydantic import BaseModel
import os
import requests

router = APIRouter(prefix="/payments", tags=["Payments"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"

class VerifyTransactionRequest(BaseModel):
    reference_id: str

@router.post("/verify-transaction")
def verify_transaction(
    payload: VerifyTransactionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reference_id = payload.reference_id
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Paystack secret key not configured.")

    # Call Paystack API to verify transaction
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.get(PAYSTACK_VERIFY_URL + reference_id, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to verify payment with Paystack.")

    data = response.json()
    if not data.get("status") or not data.get("data"):
        raise HTTPException(status_code=400, detail="Invalid response from Paystack.")

    payment = data["data"]
    if (
        payment.get("status") == "success"
        and payment.get("amount") == 100  # Paystack amount is in cents (1.00 USD = 100 cents)
        and payment.get("currency", "").upper() == "USD"
    ):
        user.is_premium = True
        user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
        db.add(user)
        db.commit()
        return {"message": "Premium activated"}
    else:
        raise HTTPException(status_code=400, detail="Payment not valid or not for the correct amount/currency.")
