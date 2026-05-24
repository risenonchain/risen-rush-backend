from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class GuardianContractScanBase(BaseModel):
    address: str
    network: str = "bsc"

class GuardianContractScanResponse(GuardianContractScanBase):
    id: int
    risk_score: Optional[int]
    is_honeypot: Optional[bool]
    buy_tax: Optional[float]
    sell_tax: Optional[float]
    owner_address: Optional[str]
    is_proxy: Optional[bool]
    has_mint_function: Optional[bool]
    is_open_source: Optional[bool]
    created_at: datetime

    class Config:
        from_attributes = True

class GuardianWatchlistCreate(BaseModel):
    target_address: str
    target_type: str  # 'contract' or 'wallet'
    label: Optional[str] = None

class GuardianWatchlistResponse(BaseModel):
    id: int
    target_address: str
    target_type: str
    label: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class GuardianAlertResponse(BaseModel):
    id: int
    severity: str
    category: str
    title: str
    message: str
    related_address: Optional[str]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
