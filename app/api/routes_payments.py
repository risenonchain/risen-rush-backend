import os
import hmac
import hashlib
import base64
import time
import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.user import User
from app.models.league import LeagueEvent, LeagueLiveAccess
from app.api.routes_auth import get_current_user
from pydantic import BaseModel
from threading import Lock

router = APIRouter(prefix="/payments", tags=["Payments"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_WEBHOOK_SECRET = os.getenv("PAYSTACK_WEBHOOK_SECRET")
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"
EXCHANGE_API_URL = "https://open.er-api.com/v6/latest/USD"

_exchange_cache = {"rate": None, "timestamp": None}
_EXCHANGE_CACHE_SECONDS = 3 * 60 * 60
_FALLBACK_RATE = 1600.0
_BUFFER = 1.02
_cache_lock = Lock()

def get_cached_exchange_rate():
    now = time.time()
    with _cache_lock:
        if _exchange_cache["rate"] and _exchange_cache["timestamp"]:
            if now - _exchange_cache["timestamp"] < _EXCHANGE_CACHE_SECONDS:
                return _exchange_cache["rate"]
        try:
            resp = requests.get(EXCHANGE_API_URL, timeout=5)
            data = resp.json()
            rate = float(data["rates"]["NGN"])
            _exchange_cache["rate"] = rate
            _exchange_cache["timestamp"] = now
            return rate
        except Exception:
            return _FALLBACK_RATE

class InitializePaymentRequest(BaseModel):
    product_id: str
    league_id: int = None
    match_id: int = None

@router.post("/initialize")
def initialize_payment(
    payload: InitializePaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    rate = get_cached_exchange_rate()

    if payload.product_id == "risen_prime_monthly":
        base_price_usd = 1.00
        ref_prefix = "PRIME"
    elif payload.product_id == "league_live_access":
        if not payload.league_id:
             raise HTTPException(status_code=400, detail="league_id required for live access")
        league = db.query(LeagueEvent).filter_by(id=payload.league_id).first()
        if not league:
             raise HTTPException(status_code=404, detail="League not found")
        base_price_usd = (league.live_fee_usd or 30) / 100
        ref_prefix = f"LIVE_L{payload.league_id}"
    else:
        raise HTTPException(status_code=400, detail="Invalid product_id")

    amount_ngn = int(base_price_usd * rate * 100 * _BUFFER)

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    paystack_payload = {
        "email": user.email,
        "amount": amount_ngn,
        "currency": "NGN",
        "reference": f"{ref_prefix}_{user.username}_{int(datetime.utcnow().timestamp())}",
        "metadata": {
            "product_id": payload.product_id,
            "league_id": payload.league_id,
            "match_id": payload.match_id
        }
    }

    try:
        resp = requests.post(PAYSTACK_INITIALIZE_URL, json=paystack_payload, headers=headers, timeout=10)
        data = resp.json()
        if not data.get("status") or not data.get("data"):
            raise HTTPException(status_code=502, detail="Paystack init failed")
        return {"checkout_url": data["data"].get("authorization_url"), "amount_ngn": amount_ngn}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Paystack error: {str(e)}")

@router.post("/verify-transaction")
def verify_transaction(
    payload: VerifyTransactionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    reference_id = payload.reference_id
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    response = requests.get(PAYSTACK_VERIFY_URL + reference_id, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Verify failed")

    data = response.json().get("data", {})
    if data.get("status") == "success":
        meta = data.get("metadata", {})
        product = meta.get("product_id")

        if product == "risen_prime_monthly":
            user.is_premium = True
            user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
            db.add(user)
        elif product == "league_live_access":
            access = LeagueLiveAccess(
                league_id=meta.get("league_id"),
                user_id=user.id,
                match_id=meta.get("match_id"),
                purchased_at=datetime.utcnow(),
                payment_reference=reference_id
            )
            db.add(access)

        db.commit()
        return {"message": "Protocol Activated"}
    else:
        raise HTTPException(status_code=400, detail="Payment failed")

class VerifyTransactionRequest(BaseModel):
    reference_id: str

@router.post("/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    if PAYSTACK_WEBHOOK_SECRET:
        expected = hmac.new(PAYSTACK_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(signature or "", expected):
            return {"status": False}
    try:
        payload = await request.json()
    except:
        return {"status": False}

    if payload.get("event") == "charge.success":
        data = payload.get("data", {})
        email = data.get("customer", {}).get("email")
        meta = data.get("metadata", {})
        product = meta.get("product_id")
        user = db.query(User).filter(User.email == email).first()
        if user:
            if product == "risen_prime_monthly":
                user.is_premium = True
                user.premium_expires_at = datetime.utcnow() + timedelta(days=30)
                db.add(user)
            elif product == "league_live_access":
                access = LeagueLiveAccess(
                    league_id=meta.get("league_id"),
                    user_id=user.id,
                    match_id=meta.get("match_id"),
                    purchased_at=datetime.utcnow(),
                    payment_reference=data.get("reference")
                )
                db.add(access)
            db.commit()
    return {"status": True}
