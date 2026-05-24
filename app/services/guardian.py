import requests
import logging
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.guardian import GuardianContractScan, GuardianAlert
from app.models.user import User
from app.core.email.resend_service import EmailService

logger = logging.getLogger(__name__)

class GuardianService:
    # GoPlus Security API Base URL
    GOPLUS_BASE_URL = "https://api.goplussecurity.com/api/v1/token_security"

    SUPPORTED_CHAINS = {
        "bsc": "56",
        "ethereum": "1",
        "eth": "1",
        "polygon": "137",
        "avalanche": "43114",
        "arbitrum": "42161",
        "base": "8453",
        "solana": "solana"
    }

    @staticmethod
    async def get_ai_explanation(db: Session, scan_id: int) -> str:
        """
        Consults RISEN AI to explain the risks found in a specific scan.
        """
        scan = db.query(GuardianContractScan).filter(GuardianContractScan.id == scan_id).first()
        if not scan:
            raise Exception("Scan record not found")

        # Prepare context for RISEN AI
        risk_details = f"""
        Contract: {scan.address}
        Risk Score: {scan.risk_score}/100
        Honeypot: {scan.is_honeypot}
        Buy Tax: {scan.buy_tax}%
        Sell Tax: {scan.sell_tax}%
        Proxy: {scan.is_proxy}
        Mintable: {scan.has_mint_function}
        Verified: {scan.is_open_source}
        """

        prompt = f"As RISEN Guardian AI, analyze this contract scan and provide a professional, concise security verdict and recommendation for a trader: {risk_details}"

        try:
            api_base = os.getenv("NEXT_PUBLIC_AI_API_URL") or "https://risen-ai-backend.onrender.com"
            # Using requests for reliability with SSL/SNI
            response = requests.post(
                f"{api_base}/ai/chat",
                json={
                    "message": prompt,
                    "session_id": f"guardian_{scan.id}",
                    "context": {"mode": "guardian"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            # Extract text from AI response
            if data.get("type") == "text":
                return data["data"]["content"]
            return "Neural interpretation failed. Please review raw metrics."
        except Exception as e:
            logger.error(f"AI Consultation failed for scan {scan_id}: {e}")
            return f"Neural uplink timeout. Basic analysis: Risk Score {scan.risk_score}."

    @staticmethod
    async def scan_contract(db: Session, address: str, network: str = "bsc", user: Optional[User] = None) -> GuardianContractScan:
        """
        Scans a contract address on supported chains using GoPlus Security API.
        """
        address = address.lower().strip()
        network = network.lower().strip()

        chain_id = GuardianService.SUPPORTED_CHAINS.get(network, "56")

        # 2. Call GoPlus API
        try:
            url = f"{GuardianService.GOPLUS_BASE_URL}/{chain_id}?contract_addresses={address}"
            # Standard requests call with minimal headers to avoid SNI confusion
            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                timeout=20.0,
                verify=False
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to fetch security data for {address} on {network}: {e}")
            raise Exception(f"Security API Error: {str(e)}")

        if data.get("code") != 1 or not data.get("result"):
            logger.warning(f"No result found for address {address} on {network}")
            raise Exception(f"No security data found for this address on {network}")

        # Find the result key in a case-insensitive way
        result = None
        for key in data["result"]:
            if key.lower() == address.lower():
                result = data["result"][key]
                break

        if not result:
            raise Exception(f"Target address data not found in API response")

        # Find the result key in a case-insensitive way
        result = None
        for key in data["result"]:
            if key.lower() == address.lower():
                result = data["result"][key]
                break

        if not result:
            raise Exception(f"Target address data not found in API response")

        # 3. Calculate Risk Score (Proprietary Logic)
        risk_score = GuardianService._calculate_risk_score(result)

        # 4. Save to Database
        scan = GuardianContractScan(
            address=address,
            network=network,
            risk_score=risk_score,
            is_honeypot=result.get("is_honeypot") == "1",
            buy_tax=float(result.get("buy_tax", 0) or 0) * 100, # Convert to percentage
            sell_tax=float(result.get("sell_tax", 0) or 0) * 100,
            owner_address=result.get("owner_address"),
            is_proxy=result.get("is_proxy") == "1",
            has_mint_function=result.get("is_mintable") == "1",
            is_open_source=result.get("is_open_source") == "1",
            raw_data=result,
            scanned_by_user_id=user.id if user else None
        )

        db.add(scan)

        # 5. If High Risk, Create Alert for User
        if risk_score > 70 and user:
            alert = GuardianAlert(
                user_id=user.id,
                severity="high" if risk_score < 90 else "critical",
                category="contract_risk",
                title=f"High Risk Detected: {address[:8]}...",
                message=f"A contract you scanned has a high risk score of {risk_score}. Honeypot: {scan.is_honeypot}",
                related_address=address
            )
            db.add(alert)

            # Send Email Alert
            if user.email:
                try:
                    EmailService.send_security_alert(
                        to_email=user.email,
                        username=user.username,
                        title=alert.title,
                        message=alert.message,
                        risk_score=risk_score
                    )
                except Exception as e:
                    logger.error(f"Failed to send security alert email: {e}")

        db.commit()
        db.refresh(scan)
        return scan

    @staticmethod
    def _calculate_risk_score(data: Dict[str, Any]) -> int:
        """
        Calculates a risk score from 0-100 based on various factors.
        """
        score = 0

        # Honeypot is automatic 100
        if data.get("is_honeypot") == "1":
            return 100

        # Taxes
        buy_tax = float(data.get("buy_tax", 0) or 0)
        sell_tax = float(data.get("sell_tax", 0) or 0)
        if buy_tax > 0.10 or sell_tax > 0.10: score += 30
        if buy_tax > 0.25 or sell_tax > 0.25: score += 40

        # Security Flags
        if data.get("is_proxy") == "1": score += 20
        if data.get("is_mintable") == "1": score += 20
        if data.get("can_take_back_ownership") == "1": score += 30
        if data.get("owner_change_balance") == "1": score += 40
        if data.get("is_open_source") == "0": score += 50

        # Cap score at 99 (100 is reserved for honeypots)
        return min(score, 99)
