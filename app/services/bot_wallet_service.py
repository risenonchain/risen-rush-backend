import logging
import os
from typing import Dict, Any, Optional
from eth_account import Account
from web3 import Web3
from sqlalchemy.orm import Session
from app.models.bot_wallet import GuardianBotWallet
from app.models.user import User
from app.utils.encryption import encrypt_private_key, decrypt_private_key
from app.core.config import settings

logger = logging.getLogger(__name__)

# Account.enable_unaudited_hdwallet_features()

class BotWalletService:
    @staticmethod
    def get_w3(network: str = "bsc"):
        rpc_url = os.getenv(f"{network.upper()}_RPC_URL") or "https://bsc-dataseed.binance.org/"
        return Web3(Web3.HTTPProvider(rpc_url))

    @staticmethod
    def create_wallet(db: Session, user: User, pin: str) -> GuardianBotWallet:
        """
        Generates a new BSC/ETH wallet for a user and stores it encrypted.
        """
        # Check if user already has a bot wallet
        existing = db.query(GuardianBotWallet).filter(GuardianBotWallet.user_id == user.id).first()
        if existing:
            return existing

        # Generate new account
        acc = Account.create()
        address = acc.address
        private_key = acc.key.hex()

        # Encrypt private key with system key + user pin
        encrypted_key = encrypt_private_key(private_key, pin)

        wallet = GuardianBotWallet(
            user_id=user.id,
            address=address,
            encrypted_private_key=encrypted_key
        )

        db.add(wallet)
        db.commit()
        db.refresh(wallet)
        return wallet

    @staticmethod
    def get_wallet_info(db: Session, user: User) -> Optional[Dict[str, Any]]:
        wallet = db.query(GuardianBotWallet).filter(GuardianBotWallet.user_id == user.id).first()
        if not wallet:
            return None

        w3 = BotWalletService.get_w3("bsc")
        balance_wei = w3.eth.get_balance(wallet.address)
        balance_bnb = w3.from_wei(balance_wei, 'ether')

        return {
            "address": wallet.address,
            "balance_bnb": float(balance_bnb),
            "network": "bsc"
        }

    @staticmethod
    async def execute_swap(db: Session, user: User, pin: str, token_in: str, token_out: str, amount_in: float):
        """
        Placeholder for swap logic.
        Will integrate with 1inch or direct Router interaction.
        """
        wallet = db.query(GuardianBotWallet).filter(GuardianBotWallet.user_id == user.id).first()
        if not wallet:
            raise Exception("No bot wallet found")

        try:
            # Decrypt key
            private_key = decrypt_private_key(wallet.encrypted_private_key, pin)
        except Exception:
            raise Exception("Invalid PIN. Decryption failed.")

        # Logic to build transaction goes here...
        return {"status": "pending", "message": "Swap initialized in Secure Layer"}
