import os
import logging
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BridgeSignerService:
    @staticmethod
    def get_validator_account():
        private_key = os.getenv("BRIDGE_VALIDATOR_KEY")
        if not private_key:
            raise Exception("BRIDGE_VALIDATOR_KEY not configured in backend")
        return Account.from_key(private_key)

    @staticmethod
    def generate_release_signature(
        user_address: str,
        token_address: str,
        amount: int,
        source_chain_id: int,
        dest_chain_id: int,
        nonce: int
    ) -> str:
        """
        Generates an ECDSA signature for the bridge release function.
        Matches Solidity: keccak256(abi.encodePacked(user, token, amount, sourceChainId, destChainId, nonce))
        """
        # 1. Standardize addresses
        user = Web3.to_checksum_address(user_address)
        token = Web3.to_checksum_address(token_address)

        # 2. Re-create the message hash exactly as Solidity's abi.encodePacked
        # Note: Web3.solidity_keccak matches abi.encodePacked
        message_hash = Web3.solidity_keccak(
            ['address', 'address', 'uint256', 'uint256', 'uint256', 'uint256'],
            [user, token, amount, source_chain_id, dest_chain_id, nonce]
        )

        # 3. Sign the hash (EIP-191)
        validator = BridgeSignerService.get_validator_account()
        message = encode_defunct(hexstr=message_hash.hex())
        signed_message = Account.sign_message(message, private_key=validator.key)

        return signed_message.signature.hex()
