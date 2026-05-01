

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
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"
EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"

# In-memory cache for exchange rate
_exchange_cache = {"rate": None, "timestamp": None}
_EXCHANGE_CACHE_SECONDS = 3 * 60 * 60  # 3 hours
_FALLBACK_RATE = 1600.0
_BUFFER = 1.02  # 2% buffer

from threading import Lock
_cache_lock = Lock()

def get_cached_exchange_rate():
    import time
    now = time.time()
    with _cache_lock:
        if _exchange_cache["rate"] and _exchange_cache["timestamp"]:
            if now - _exchange_cache["timestamp"] < _EXCHANGE_CACHE_SECONDS:
                return _exchange_cache["rate"]
        # Fetch new rate
        try:
            resp = requests.get(EXCHANGE_API_URL, timeout=5)
            data = resp.json()
            rate = float(data["rates"]["NGN"])
            # Cache
            _exchange_cache["rate"] = rate
            _exchange_cache["timestamp"] = now
            return rate
        except Exception:
            # Fallback
            return _FALLBACK_RATE

class InitializePaymentRequest(BaseModel):
    product_id: str

@router.post("/initialize")
def initialize_payment(
    payload: InitializePaymentRequest,
    user: User = Depends(get_current_user)
):
    if payload.product_id != "risen_prime_monthly":
        raise HTTPException(status_code=400, detail="Invalid product_id")

    rate = get_cached_exchange_rate()
    base_price_usd = 1.00
    amount_ngn = int(base_price_usd * rate * 100 * _BUFFER)

    # Prepare Paystack initialize
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    paystack_payload = {
        "email": user.email,
        "amount": amount_ngn,
        "currency": "NGN",
        "reference": f"PRIME_{user.username}_{int(datetime.utcnow().timestamp())}",
        "callback_url": None,
        "metadata": {"product_id": payload.product_id}
    }
    try:
        resp = requests.post(PAYSTACK_INITIALIZE_URL, json=paystack_payload, headers=headers, timeout=10)
        data = resp.json()
        if not data.get("status") or not data.get("data"):
            raise HTTPException(status_code=502, detail="Paystack init failed")
        checkout_url = data["data"].get("authorization_url")
        if not checkout_url:
            raise HTTPException(status_code=502, detail="Paystack did not return checkout url")
        return {"checkout_url": checkout_url, "amount_ngn": amount_ngn, "rate": rate}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Paystack error: {str(e)}")

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
