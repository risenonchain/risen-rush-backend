from fastapi import APIRouter, HTTPException, Depends
from typing import Any
from app.services.bridge_service import BridgeService
from app.api.routes_auth import get_current_user
from app.models.user import User

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
