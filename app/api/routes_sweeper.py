from fastapi import APIRouter, HTTPException, Depends
from typing import List, Any
from app.services.sweeper_service import SweeperService
from app.api.routes_auth import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter(prefix="/sweeper", tags=["Dust Sweeper"])

@router.get("/scan")
async def scan_wallet_dust(
    address: str,
    chain: str = "bsc",
    current_user: User = Depends(get_current_user)
):
    """
    Scan a wallet for fragmented balances.
    """
    try:
        return await SweeperService.scan_dust(address, chain, settings.moralis_api_key)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/convert")
async def convert_dust(
    address: str,
    tokens: List[str],
    current_user: User = Depends(get_current_user)
):
    """
    Initialize the sweep to $RSN protocol.
    """
    try:
        return await SweeperService.convert_to_rsn(address, tokens)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
