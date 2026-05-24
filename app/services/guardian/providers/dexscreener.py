import requests
import logging
from typing import Dict, Any, Optional
from .base import SecurityProvider

logger = logging.getLogger(__name__)

class DexScreenerProvider(SecurityProvider):
    BASE_URL = "https://api.dexscreener.com/latest/dex/tokens"

    async def scan(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        """
        Fetches liquidity and market data from DexScreener.
        """
        try:
            url = f"{self.BASE_URL}/{address}"
            response = requests.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            if not data.get("pairs"):
                return None

            # Get the best pair (highest liquidity)
            best_pair = sorted(data["pairs"], key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)[0]

            return {
                "liquidity_usd": best_pair.get("liquidity", {}).get("usd", 0),
                "fdv": best_pair.get("fdv", 0),
                "pair_address": best_pair.get("pairAddress"),
                "base_token": best_pair.get("baseToken"),
                "volume_24h": best_pair.get("volume", {}).get("h24", 0)
            }
        except Exception as e:
            logger.error(f"DexScreener Provider Error: {e}")
            return None
