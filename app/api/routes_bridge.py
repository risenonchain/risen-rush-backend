from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Any
from datetime import datetime
from app.db.database import get_db
from app.services.bridge_service import BridgeService
from app.services.bridge_signer import BridgeSignerService
from app.api.routes_auth import get_current_user
from app.models.user import User
from app.models.bridge import BridgeTransaction

router = APIRouter(prefix="/bridge", tags=["Neural Bridge"])

@router.get("/quote")
def get_bridge_quote(
    from_chain: str,
    to_chain: str,
    amount: float,
    current_user: User = Depends(get_current_user)
):
    """
    Get a quote for cross-chain migration.
    """
    try:
        return BridgeService.get_quote(from_chain, to_chain, amount)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/claim-signature")
async def request_claim_signature(
    source_tx_hash: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verifies a source chain deposit and returns the validator signature for release.
    """
    # 1. Check if we already processed this tx
    tx = db.query(BridgeTransaction).filter(BridgeTransaction.source_tx_hash == source_tx_hash).first()

    if tx and tx.signature:
        return {"signature": tx.signature, "amount": str(tx.amount), "nonce": str(tx.nonce)}

    # 2. Mock data for demonstration (In production, verify on-chain event here)
    mock_nonce = int(datetime.utcnow().timestamp())
    mock_amount = 1000 * 10**18 # 1000 Tokens

    try:
        signature = BridgeSignerService.generate_release_signature(
            user_address=current_user.wallet_address or "0x0000000000000000000000000000000000000000",
            token_address="0x0000000000000000000000000000000000000000", # Example
            amount=mock_amount,
            source_chain_id=56, # BSC
            dest_chain_id=137,  # Polygon
            nonce=mock_nonce
        )

        # Save record
        new_tx = BridgeTransaction(
            user_address=current_user.wallet_address or "0x0000000000000000000000000000000000000000",
            token_address="0x0000000000000000000000000000000000000000",
            amount=mock_amount,
            source_chain_id=56,
            dest_chain_id=137,
            source_tx_hash=source_tx_hash,
            nonce=mock_nonce,
            signature=signature
        )
        db.add(new_tx)
        db.commit()

        return {"signature": signature, "amount": str(mock_amount), "nonce": str(mock_nonce)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signer Error: {str(e)}")
