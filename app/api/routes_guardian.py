from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.routes_auth import get_current_user
from app.models.user import User
from app.models.guardian import GuardianContractScan, GuardianWatchlist, GuardianAlert
from app.services.guardian import GuardianService
from app.services.monitoring.wallet_service import WalletIntelligenceService
from app.schemas.guardian import (
    GuardianContractScanResponse,
    GuardianWatchlistCreate,
    GuardianWatchlistResponse,
    GuardianAlertResponse
)

router = APIRouter(prefix="/guardian", tags=["Guardian Security"])

@router.get("/scan/{address}", response_model=GuardianContractScanResponse)
async def scan_contract(
    address: str,
    network: str = "bsc",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Scan a smart contract address for security risks.
    Supported networks: bsc, ethereum, polygon, avalanche, arbitrum, base, solana
    Non-premium users are limited to 5 scans per 24 hours.
    """
    # Premium Check
    if current_user and not current_user.is_premium:
        # Check today's scan count
        from datetime import datetime, timedelta
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        scan_count = db.query(GuardianContractScan).filter(
            GuardianContractScan.scanned_by_user_id == current_user.id,
            GuardianContractScan.created_at >= twenty_four_hours_ago
        ).count()

        if scan_count >= 5:
            raise HTTPException(
                status_code=403,
                detail="Daily scan limit reached. Upgrade to RISEN Prime for unlimited scans."
            )

    try:
        scan = await GuardianService.scan_contract(db=db, address=address, network=network, user=current_user)
        return scan
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/watchlist", response_model=GuardianWatchlistResponse)
def add_to_watchlist(
    payload: GuardianWatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a contract or wallet to the user's security watchlist.
    """
    # Check if already in watchlist
    existing = db.query(GuardianWatchlist).filter(
        GuardianWatchlist.user_id == current_user.id,
        GuardianWatchlist.target_address == payload.target_address.lower()
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Address already in watchlist")

    item = GuardianWatchlist(
        user_id=current_user.id,
        target_address=payload.target_address.lower(),
        target_type=payload.target_type,
        label=payload.label
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.get("/watchlist", response_model=List[GuardianWatchlistResponse])
def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the user's security watchlist.
    """
    return db.query(GuardianWatchlist).filter(GuardianWatchlist.user_id == current_user.id).all()

@router.get("/alerts", response_model=List[GuardianAlertResponse])
def get_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = False
):
    """
    Get security alerts for the current user.
    """
    query = db.query(GuardianAlert).filter(GuardianAlert.user_id == current_user.id)
    if unread_only:
        query = query.filter(GuardianAlert.is_read == False)

    return query.order_by(GuardianAlert.created_at.desc()).all()

@router.patch("/alerts/{alert_id}/read")
def mark_alert_as_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark a specific alert as read.
    """
    alert = db.query(GuardianAlert).filter(
        GuardianAlert.id == alert_id,
        GuardianAlert.user_id == current_user.id
    ).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    db.commit()
    return {"status": "success"}

@router.get("/wallet/analyze/{address}")
async def analyze_wallet(
    address: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Analyze a wallet address for risk.
    """
    try:
        result = await WalletIntelligenceService.analyze_wallet(db=db, address=address, current_user=current_user, network="bsc")
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/scan/{scan_id}/explain")
async def explain_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get an AI-powered explanation of a specific scan.
    Exclusive to RISEN Prime users.
    """
    if not current_user.is_premium:
        raise HTTPException(
            status_code=403,
            detail="AI Verdicts are exclusive to RISEN Prime members."
        )

    try:
        explanation = await GuardianService.get_ai_explanation(db, scan_id)
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
