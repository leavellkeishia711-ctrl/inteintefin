import asyncio
import os
import argparse
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.db.session import system_session
from app.db.models.connectors import ConnectorConfig

async def rotate_keys(old_key: str, new_key: str):
    """
    Rotates the encryption key for all connector secrets in the database.
    Reads with old_key, encrypts with new_key.
    """
    try:
        old_cipher = Fernet(old_key.encode('utf-8'))
        new_cipher = Fernet(new_key.encode('utf-8'))
    except Exception as e:
        print(f"Failed to initialize ciphers: {e}")
        return

    async with system_session() as db:
        stmt = select(ConnectorConfig)
        result = await db.execute(stmt)
        configs = result.scalars().all()

        updated_count = 0
        for config in configs:
            try:
                decrypted = old_cipher.decrypt(config.encrypted_secret.encode('utf-8')).decode('utf-8')
                new_encrypted = new_cipher.encrypt(decrypted.encode('utf-8')).decode('utf-8')
                config.encrypted_secret = new_encrypted
                updated_count += 1
            except Exception as e:
                print(f"Failed to rotate key for connector {config.id} (Company: {config.company_id}): {e}")
        
        await db.commit()
        print(f"Successfully rotated {updated_count} connector keys.")

def main():
    parser = argparse.ArgumentParser(description="Rotate connector encryption keys")
    parser.add_argument("--old-key", required=True, help="The current CONNECTOR_SECRET_KEY")
    parser.add_argument("--new-key", required=True, help="The new CONNECTOR_SECRET_KEY")
    args = parser.parse_args()

    asyncio.run(rotate_keys(args.old_key, args.new_key))

if __name__ == "__main__":
    main()
