import requests
import logging
from typing import Dict, Any, Optional
from .base import SecurityProvider

logger = logging.getLogger(__name__)

class GoPlusProvider(SecurityProvider):
    # Updated reliable URL
    BASE_URL = "https://api.gopluslabs.io/api/v1/token_security"

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

    async def scan(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        chain_id = self.SUPPORTED_CHAINS.get(chain.lower(), "56")
        url = f"{self.BASE_URL}/{chain_id}?contract_addresses={address}"

        try:
            # Using requests for reliability with SSL/SNI
            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                },
                timeout=15.0,
                verify=False # Bypass strict SSL for this specific SNI issue
            )
            response.raise_for_status()
            data = response.json()

            if data.get("code") != 1 or not data.get("result"):
                return None

            # Case-insensitive lookup
            for key in data["result"]:
                if key.lower() == address.lower():
                    return data["result"][key]

            return None
        except Exception as e:
            logger.error(f"GoPlus Provider Error: {e}")
            return None
