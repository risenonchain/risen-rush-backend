import requests
import logging
from typing import Dict, Any, Optional
from .base import SecurityProvider

logger = logging.getLogger(__name__)

class HoneypotIsProvider(SecurityProvider):
    # This provider focuses on Honeypot.is V2 API
    BASE_URL = "https://api.honeypot.is/v2/IsHoneypot"

    CHAIN_MAP = {
        "bsc": "56",
        "ethereum": "1",
        "polygon": "137",
        "base": "8453",
        "arbitrum": "42161"
    }

    async def scan(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Performs a honeypot simulation via Honeypot.is
        """
        chain_id = self.CHAIN_MAP.get(chain.lower(), "56")
        try:
            url = f"{self.BASE_URL}?address={address}&chainID={chain_id}"
            response = requests.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if not data.get("honeypotResult"):
                return None

            res = data["honeypotResult"]
            return {
                "is_honeypot": res.get("isHoneypot"),
                "buy_tax": data.get("simulationResult", {}).get("buyTax", 0),
                "sell_tax": data.get("simulationResult", {}).get("sellTax", 0),
                "transfer_tax": data.get("simulationResult", {}).get("transferTax", 0),
                "simulation_success": data.get("simulationSuccess", False)
            }
        except Exception as e:
            logger.error(f"Honeypot.is Provider Error: {e}")
            return None
