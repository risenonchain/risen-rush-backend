import logging
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.guardian import GuardianContractScan, GuardianAlert
from app.models.user import User
from app.core.email.resend_service import EmailService

# Internal Package Imports
from .providers.goplus import GoPlusProvider
from .providers.dexscreener import DexScreenerProvider
from .providers.honeypot import HoneypotIsProvider
from .intelligence.risk_engine import RiskEngine

logger = logging.getLogger(__name__)

class GuardianService:
    @staticmethod
    async def scan_contract(db: Session, address: str, network: str = "bsc", user: Optional[User] = None) -> GuardianContractScan:
        """
        Scans a contract address using multiple providers and calculates a deterministic risk score.
        """
        address = address.lower().strip()
        network = network.lower().strip()

        # 1. Gather Data from Providers
        providers_data = {}

        # parallel execution would be better but keeping it simple for stability
        # GoPlus
        goplus = GoPlusProvider()
        providers_data["goplus"] = await goplus.scan(address, network)

        # DexScreener
        dex = DexScreenerProvider()
        providers_data["dexscreener"] = await dex.scan(address, network)

        # Honeypot.is
        hp = HoneypotIsProvider()
        providers_data["honeypot_is"] = await hp.scan(address, network)

        logger.info(f"Scan complete for {address}. GoPlus: {bool(providers_data['goplus'])}, Dex: {bool(providers_data['dexscreener'])}, HP: {bool(providers_data['honeypot_is'])}")

        # Fallback Logic: If everything fails, we raise an error
        if not providers_data["goplus"] and not providers_data["honeypot_is"]:
             raise Exception(f"No security data found for this address across all providers.")

        # 2. Calculate Deterministic Risk Score
        risk_score = RiskEngine.calculate_score(providers_data)

        result = providers_data["goplus"] # Using primary provider for database fields

        # 3. Save to Database
        scan = GuardianContractScan(
            address=address,
            network=network,
            risk_score=risk_score,
            is_honeypot=result.get("is_honeypot") == "1" if result else False,
            buy_tax=float(result.get("buy_tax", 0) or 0) * 100 if result else 0,
            sell_tax=float(result.get("sell_tax", 0) or 0) * 100 if result else 0,
            owner_address=result.get("owner_address") if result else None,
            is_proxy=result.get("is_proxy") == "1" if result else False,
            has_mint_function=result.get("is_mintable") == "1" if result else False,
            is_open_source=result.get("is_open_source") == "1" if result else True,
            raw_data=result,
            scanned_by_user_id=user.id if user else None
        )

        db.add(scan)

        # 4. Handle Alerts
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

            # TODO: Move to shared event-driven notification system
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
    async def get_ai_explanation(db: Session, scan_id: int) -> str:
        """
        AI is only used for EXPLANATION, never for SCORING.
        """
        import requests
        scan = db.query(GuardianContractScan).filter(GuardianContractScan.id == scan_id).first()
        if not scan:
            raise Exception("Scan record not found")

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

        prompt = f"As RISEN Guardian AI, explain the security risks of this contract and provide a trader recommendation: {risk_details}"

        try:
            # Match the variable name in your Vercel/Production env
            api_base = os.getenv("NEXT_PUBLIC_AI_API_URL") or os.getenv("AI_API_URL") or "https://risen-ai-backend.onrender.com"
            response = requests.post(
                f"{api_base}/ai/chat",
                json={
                    "message": prompt,
                    "session_id": f"guardian_{scan.id}",
                    "context": {"mode": "guardian"}
                },
                headers={
                    "Content-Type": "application/json",
                    "X-App-Version": "1.1.0"
                },
                timeout=25.0
            )
            response.raise_for_status()
            data = response.json()
            if data.get("type") == "text":
                return data["data"]["content"]
            return "Neural interpretation failed. Please review raw metrics."
        except Exception as e:
            logger.error(f"AI Consultation failed for scan {scan_id}: {e}")
            return f"Neural uplink timeout. Basic analysis: Risk Score {scan.risk_score}."
