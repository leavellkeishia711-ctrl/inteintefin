from cryptography.fernet import Fernet
import os

def get_cipher() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError("ENCRYPTION_KEY environment variable is not set")
    return Fernet(key.encode('utf-8'))

def encrypt_secret(secret: str) -> str:
    cipher = get_cipher()
    return cipher.encrypt(secret.encode('utf-8')).decode('utf-8')

def decrypt_secret(encrypted_secret: str) -> str:
    cipher = get_cipher()
    return cipher.decrypt(encrypted_secret.encode('utf-8')).decode('utf-8')
