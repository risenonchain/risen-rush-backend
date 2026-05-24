import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings

def get_derived_key(user_pin: str) -> bytes:
    """
    Derives a encryption key from the user PIN and system secret.
    """
    salt = settings.secret_key.encode()[:16] # Use system secret as salt
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(user_pin.encode()))
    return key

def encrypt_private_key(private_key: str, user_pin: str) -> str:
    key = get_derived_key(user_pin)
    f = Fernet(key)
    return f.encrypt(private_key.encode()).decode()

def decrypt_private_key(encrypted_key: str, user_pin: str) -> str:
    key = get_derived_key(user_pin)
    f = Fernet(key)
    return f.decrypt(encrypted_key.encode()).decode()
