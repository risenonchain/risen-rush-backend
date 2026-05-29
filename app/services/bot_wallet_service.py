import logging
import os
import time
from typing import Dict, Any, Optional, List
from eth_account import Account
from web3 import Web3
from sqlalchemy.orm import Session
from app.models.bot_wallet import GuardianBotWallet
from app.models.user import User
from app.utils.encryption import encrypt_private_key, decrypt_private_key
from app.core.config import settings

logger = logging.getLogger(__name__)

# Standard ABIs
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"success","type":"bool"}],"type":"function"}]'
PANCAKE_ROUTER_ABI = '[{"inputs":[{"amountOutMin":"uint256","path":"address[]","to":"address","deadline":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"amounts":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"amountIn":"uint256","amountOutMin":"uint256","path":"address[]","to":"address","deadline":"uint256"}],"name":"swapExactTokensForETHSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"}]'

PANCAKE_ROUTER_ADDRESS = "0x10ED43C718714eb63d5aA57B78B54704E256024E" # Mainnet V2
WBNB_ADDRESS = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"

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

        # Add Token Portfolio (Checking $RSN and others)
        tokens = [
            {"name": "RISEN", "symbol": "RSN", "address": os.getenv("RSN_CONTRACT_ADDRESS", "0x...")}
        ]

        portfolio = []
        for t in tokens:
            if t["address"] == "0x...": continue
            try:
                # Basic ERC20 ABI for balance
                abi = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]'
                contract = w3.eth.contract(address=w3.to_checksum_address(t["address"]), abi=abi)
                bal = contract.functions.balanceOf(wallet.address).call()
                if bal > 0:
                    portfolio.append({
                        "name": t["name"],
                        "symbol": t["symbol"],
                        "balance": float(w3.from_wei(bal, 'ether'))
                    })
            except: pass

        return {
            "address": wallet.address,
            "balance_bnb": float(balance_bnb),
            "portfolio": portfolio,
            "network": "bsc"
        }

    @staticmethod
    async def execute_pancake_buy(db: Session, user: User, pin: str, token_address: str, amount_bnb: float):
        """
        Executes a token buy on PancakeSwap using the bot wallet.
        Supports tokens with fees on transfer.
        """
        wallet = db.query(GuardianBotWallet).filter(GuardianBotWallet.user_id == user.id).first()
        if not wallet: raise Exception("No bot wallet found")

        try:
            priv_key = decrypt_private_key(wallet.encrypted_private_key, pin)
        except: raise Exception("Invalid PIN")

        w3 = BotWalletService.get_w3("bsc")
        account = Account.from_key(priv_key)

        router = w3.eth.contract(address=w3.to_checksum_address(PANCAKE_ROUTER_ADDRESS), abi=PANCAKE_ROUTER_ABI)

        # Build Tx
        nonce = w3.eth.get_transaction_count(account.address)
        path = [w3.to_checksum_address(WBNB_ADDRESS), w3.to_checksum_address(token_address)]

        # Use swapExactETHForTokensSupportingFeeOnTransferTokens for compatibility with meme tokens
        tx = router.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
            0, # amountOutMin
            path,
            account.address,
            int(time.time()) + 600
        ).build_transaction({
            'from': account.address,
            'value': w3.to_wei(amount_bnb, 'ether'),
            'gas': 350000, # Increased gas for taxable tokens
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=priv_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return {"status": "success", "tx_hash": tx_hash.hex()}

    @staticmethod
    async def execute_pancake_sell(db: Session, user: User, pin: str, token_address: str, percentage: float):
        """
        Executes a token sell on PancakeSwap.
        """
        wallet = db.query(GuardianBotWallet).filter(GuardianBotWallet.user_id == user.id).first()
        if not wallet: raise Exception("No bot wallet found")

        try:
            priv_key = decrypt_private_key(wallet.encrypted_private_key, pin)
        except: raise Exception("Invalid PIN")

        w3 = BotWalletService.get_w3("bsc")
        account = Account.from_key(priv_key)

        # 1. Get Token Balance
        token_contract = w3.eth.contract(address=w3.to_checksum_address(token_address), abi=ERC20_ABI)
        full_balance = token_contract.functions.balanceOf(account.address).call()

        if full_balance == 0: raise Exception("No tokens to sell")

        amount_to_sell = int(full_balance * (percentage / 100))

        # 2. Approve Router
        nonce = w3.eth.get_transaction_count(account.address)
        approve_tx = token_contract.functions.approve(
            w3.to_checksum_address(PANCAKE_ROUTER_ADDRESS),
            amount_to_sell
        ).build_transaction({
            'from': account.address,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })

        signed_approve = w3.eth.account.sign_transaction(approve_tx, private_key=priv_key)
        w3.eth.send_raw_transaction(signed_approve.raw_transaction)

        # 3. Swap
        time.sleep(2) # Wait a bit for approval to propagate

        router = w3.eth.contract(address=w3.to_checksum_address(PANCAKE_ROUTER_ADDRESS), abi=PANCAKE_ROUTER_ABI)
        path = [w3.to_checksum_address(token_address), w3.to_checksum_address(WBNB_ADDRESS)]

        swap_tx = router.functions.swapExactTokensForETHSupportingFeeOnTransferTokens(
            amount_to_sell,
            0,
            path,
            account.address,
            int(time.time()) + 600
        ).build_transaction({
            'from': account.address,
            'gas': 350000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce + 1,
        })

        signed_swap = w3.eth.account.sign_transaction(swap_tx, private_key=priv_key)
        tx_hash = w3.eth.send_raw_transaction(signed_swap.raw_transaction)

        return {"status": "success", "tx_hash": tx_hash.hex()}
