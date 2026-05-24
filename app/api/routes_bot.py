from fastapi import APIRouter, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.db.database import get_db
from app.core.config import settings
from app.models.user import User
from app.services.bot_wallet_service import BotWalletService

router = APIRouter(prefix="/bot", tags=["Infrastructure Bot Internal"])

def verify_bot_secret(x_bot_secret: str = Header(...)):
    if x_bot_secret != settings.bot_token: # Using bot_token as secret for simple validation
        raise HTTPException(status_code=403, detail="Unauthorized bot access")

@router.post("/link")
def link_telegram(chat_id: str, email: str, db: Session = Depends(get_db), _ = Depends(verify_bot_secret)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.telegram_chat_id = chat_id
    db.commit()
    return {"status": "success", "message": f"Telegram linked to {email}"}

@router.get("/wallet/{chat_id}")
def get_bot_wallet(chat_id: str, db: Session = Depends(get_db), _ = Depends(verify_bot_secret)):
    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not linked. Use /link")

    info = BotWalletService.get_wallet_info(db, user)
    if not info:
        return {"status": "empty", "message": "No wallet generated yet. Use /create_wallet"}

    return info

@router.post("/wallet/create")
def create_bot_wallet(chat_id: str, pin: str, db: Session = Depends(get_db), _ = Depends(verify_bot_secret)):
    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not linked")

    if len(pin) < 4:
        raise HTTPException(status_code=400, detail="PIN must be at least 4 digits")

    wallet = BotWalletService.create_wallet(db, user, pin)
    return {"status": "success", "address": wallet.address}

@router.post("/trade/buy")
async def bot_trade_buy(
    chat_id: str,
    pin: str,
    token_address: str,
    amount_bnb: float,
    db: Session = Depends(get_db),
    _ = Depends(verify_bot_secret)
):
    """
    Executes a buy order via the bot.
    """
    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    if not user: raise HTTPException(status_code=404, detail="Account not linked")

    try:
        result = await BotWalletService.execute_pancake_buy(db, user, pin, token_address, amount_bnb)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
