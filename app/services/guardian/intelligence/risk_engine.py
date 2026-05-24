from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class RiskEngine:
    @staticmethod
    def calculate_score(data_map: Dict[str, Any]) -> int:
        """
        Aggregates data from multiple providers to calculate a unified risk score (0-100).
        """
        score = 0
        goplus = data_map.get("goplus")
        honeypot_is = data_map.get("honeypot_is")
        dexscreener = data_map.get("dexscreener")

        # 1. Honeypot check (CRITICAL)
        # We check both GoPlus and Honeypot.is for maximum safety
        is_honeypot = False
        if goplus and goplus.get("is_honeypot") == "1": is_honeypot = True
        if honeypot_is and honeypot_is.get("is_honeypot") is True: is_honeypot = True

        if is_honeypot:
            return 100

        # 2. Taxes (Aggregate data)
        # We take the higher tax value between providers to be safe
        buy_tax = 0.0
        sell_tax = 0.0

        if goplus:
            buy_tax = max(buy_tax, float(goplus.get("buy_tax", 0) or 0))
            sell_tax = max(sell_tax, float(goplus.get("sell_tax", 0) or 0))

        if honeypot_is:
            buy_tax = max(buy_tax, float(honeypot_is.get("buy_tax", 0) or 0) / 100) # Honeypot.is uses % integers
            sell_tax = max(sell_tax, float(honeypot_is.get("sell_tax", 0) or 0) / 100)

        if buy_tax > 0.10 or sell_tax > 0.10: score += 20
        if buy_tax > 0.25 or sell_tax > 0.25: score += 30
        if buy_tax > 0.50 or sell_tax > 0.50: score += 40

        # 3. Liquidity (DexScreener)
        if dexscreener:
            liquidity = dexscreener.get("liquidity_usd", 0)
            if liquidity < 5000: score += 50 # Micro liquidity = High rug risk
            elif liquidity < 20000: score += 30
            elif liquidity < 50000: score += 10
        else:
            score += 20 # No liquidity data = cautious

        # 4. Security Flags (GoPlus)
        if goplus:
            if goplus.get("is_proxy") == "1": score += 20
            if goplus.get("is_mintable") == "1": score += 20
            if goplus.get("can_take_back_ownership") == "1": score += 30
            if goplus.get("is_open_source") == "0": score += 50

        # Cap score at 99 (100 is reserved for confirmed honeypots)
        return min(score, 99)
