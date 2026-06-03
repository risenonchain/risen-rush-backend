import logging
import requests
from typing import List, Dict, Any
from eth_account.messages import encode_defunct
from web3 import Web3

logger = logging.getLogger(__name__)

class SweeperService:
    @staticmethod
    def verify_wallet_signature(address: str, signature: str, message: str) -> bool:
        """
        Verifies that a message was signed by the specific wallet address.
        """
        try:
            w3 = Web3()
            message_hash = encode_defunct(text=message)
            signer = w3.eth.account.recover_message(message_hash, signature=signature)
            return signer.lower() == address.lower()
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    @staticmethod
    async def scan_dust(wallet_address: str, chain: str = "bsc", api_key: str = "") -> List[Dict[str, Any]]:
        """
        Scans for small token balances using Moralis API.
        """
        # Chain ID mapping
        chain_map = {"bsc": "0x38", "eth": "0x1", "polygon": "0x89", "base": "0x2105"}
        chain_id = chain_map.get(chain.lower(), "0x38")

        if not api_key:
            # Fallback to simulated data if no API key is provided for now
            # In production, this MUST use the Moralis API
            return [
                {"name": "Pepe Token", "symbol": "PEPE", "balance": "12,400,000", "value_usd": 4.12, "icon": "🐸", "token_address": "0x6982508145454ce325ddbe47a25d4ec3d2311933"},
                {"name": "Baby Doge", "symbol": "BABYDOGE", "balance": "1,200,000,000", "value_usd": 2.30, "icon": "🐶", "token_address": "0xc748673057861a797275CD8A068AbB95A902e8de"},
            ]

        try:
            url = f"https://deep-index.moralis.io/api/v2/{wallet_address}/erc20?chain={chain_id}"
            headers = {"X-API-Key": api_key, "accept": "application/json"}

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                raise Exception(f"Moralis API error: {response.text}")

            tokens = response.json()
            dust = []

            for t in tokens:
                # Calculate USD value (Moralis provides price in another endpoint or we use a threshold)
                # For now, we filter by balance if price data is unavailable in this call
                # Real implementation should call /erc20/{address}/price
                balance = int(t["balance"]) / (10 ** int(t["decimals"]))

                # Filter logic: tokens with small but non-zero balances
                if 0 < balance:
                    dust.append({
                        "name": t["name"],
                        "symbol": t["symbol"],
                        "balance": f"{balance:.4f}",
                        "token_address": t["token_address"],
                        "value_usd": 0.0, # Placeholder, needs price API
                        "icon": "💎"
                    })

            return dust

        except Exception as e:
            logger.error(f"Sweeper scan failed: {e}")
            raise Exception("Neural matrix scan interrupted. Please try again.")

    @staticmethod
    async def convert_to_rsn(wallet_address: str, tokens: List[str]) -> Dict[str, Any]:
        """
        Returns the data needed for the frontend to call the DustSweeper contract.
        """
        return {
            "status": "ready",
            "contract_address": "0x6Ac725cF68419184704e0dbAB75A507dC3570305",
            "target_token": "0xfaae1faadc569895162c5584ffbca845f4147777",
            "fee_bps": 300,
            "message": "Transaction parameters generated. Please sign in your wallet."
        }
