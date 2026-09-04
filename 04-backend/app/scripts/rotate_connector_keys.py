import asyncio
import os
import argparse
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.db.session import system_session
from app.db.models.connectors import ConnectorConfig

async def rotate_keys(old_key: str, new_key: str, db=None, dry_run=False):
    """
    Rotates the encryption key for all connector secrets in the database.
    Reads with old_key, encrypts with new_key.
    """
    old_cipher = Fernet(old_key.encode('utf-8'))
    new_cipher = Fernet(new_key.encode('utf-8'))

    session = db if db else system_session()
    
    # We shouldn't use `async with session:` because if db is passed from tests, it closes it.
    # We will just use it directly, and only commit if not dry_run.
    stmt = select(ConnectorConfig)
    result = await session.execute(stmt)
    configs = result.scalars().all()

    updated_count = 0
    for config in configs:
        try:
            # Note: the property is `encrypted_credentials` not `encrypted_secret`
            if hasattr(config, 'encrypted_secret'):
                attr = 'encrypted_secret'
            else:
                attr = 'encrypted_credentials'
            
            val = getattr(config, attr)
            if not val:
                continue
                
            decrypted = old_cipher.decrypt(val.encode('utf-8')).decode('utf-8')
            new_encrypted = new_cipher.encrypt(decrypted.encode('utf-8')).decode('utf-8')
            
            setattr(config, attr, new_encrypted)
            updated_count += 1
        except Exception as e:
            if not db: # only print if not in test
                print(f"Failed to rotate key for connector {config.id} (Company: {config.company_id}): {e}")
            await session.rollback()
            raise e
    
    if not dry_run:
        await session.commit()
    
    if not db:
        await session.close()
        
    print(f"Successfully rotated {updated_count} connector keys.")

def main():
    parser = argparse.ArgumentParser(description="Rotate connector encryption keys")
    parser.add_argument("--old-key", required=True, help="The current CONNECTOR_SECRET_KEY")
    parser.add_argument("--new-key", required=True, help="The new CONNECTOR_SECRET_KEY")
    args = parser.parse_args()

    asyncio.run(rotate_keys(args.old_key, args.new_key))

if __name__ == "__main__":
    main()
