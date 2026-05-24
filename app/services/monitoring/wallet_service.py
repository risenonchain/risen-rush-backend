import requests
import logging
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.guardian import GuardianAlert
from app.models.user import User
from app.core.email.resend_service import EmailService

from ..guardian.providers.goplus import GoPlusProvider

logger = logging.getLogger(__name__)

class WalletIntelligenceService:
    @staticmethod
    async def analyze_wallet(db: Session, address: str, user: Optional[User] = None, network: str = "bsc") -> Dict[str, Any]:
        """
        Analyzes a wallet address for malicious behavior or risk.
        """
        address = address.lower().strip()
        network = network.lower().strip()

        # 1. Use GoPlus Provider
        goplus = GoPlusProvider()
        # Note: Address security uses a different endpoint,
        # but we can reuse the chain mapping.
        chain_id = goplus.SUPPORTED_CHAINS.get(network, "56")

        try:
            # Correct GoPlus Address API Format
            url = f"https://api.gopluslabs.io/api/v1/address_security/{address}?chain_id={chain_id}"
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15.0,
                verify=False
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 1 or not data.get("result"):
                raise Exception("No security data found for this wallet")

            result = data["result"]
        except Exception as e:
            logger.error(f"Wallet analysis failed: {e}")
            raise Exception(f"Wallet Security API Error: {str(e)}")

        # Risk factors
        is_malicious = result.get("is_blacklisted") == "1" or result.get("is_honeypot_related") == "1"
        risk_score = 0
        if is_malicious: risk_score = 100
        elif result.get("data_source"): risk_score = 20 # Basic score for active wallets

        # If malicious and we have a user, alert them
        if is_malicious and user:
            alert = GuardianAlert(
                user_id=user.id,
                severity="critical",
                category="wallet_activity",
                title=f"Malicious Wallet Flagged: {address[:8]}...",
                message=f"The wallet {address} has been flagged as malicious or blacklisted by security protocols.",
                related_address=address
            )
            db.add(alert)

            if user.email:
                try:
                    EmailService.send_security_alert(
                        to_email=user.email,
                        username=user.username,
                        title="Critical: Malicious Wallet Detected",
                        message=alert.message,
                        risk_score=100
                    )
                except Exception as e:
                    logger.error(f"Email alert failed: {e}")

            db.commit()

        return {
            "address": address,
            "risk_score": risk_score,
            "is_malicious": is_malicious,
            "details": result
        }
