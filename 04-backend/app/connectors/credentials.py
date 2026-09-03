from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger(__name__)

def get_cipher() -> Fernet:
    key = os.getenv("CONNECTOR_SECRET_KEY")
    if not key:
        raise ValueError("CONNECTOR_SECRET_KEY environment variable is not set")
    try:
        return Fernet(key.encode('utf-8'))
    except Exception:
        raise ValueError("CONNECTOR_SECRET_KEY is invalid")

def encrypt_secret(secret: str) -> str:
    if not secret:
        raise ValueError("Cannot encrypt empty secret")
    cipher = get_cipher()
    return cipher.encrypt(secret.encode('utf-8')).decode('utf-8')

def decrypt_secret(encrypted_secret: str) -> str:
    if not encrypted_secret:
        raise ValueError("Cannot decrypt empty secret")
    cipher = get_cipher()
    try:
        return cipher.decrypt(encrypted_secret.encode('utf-8')).decode('utf-8')
    except Exception:
        logger.error("Failed to decrypt connector secret")
        raise ValueError("Invalid encrypted secret")
