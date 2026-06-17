import base64
import hashlib

from cryptography.fernet import Fernet

from app.config import settings


def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(settings.encryption_key.encode()).digest()
    key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
