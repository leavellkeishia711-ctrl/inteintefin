import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.db.models.connectors import ConnectorConfig
from app.scripts.rotate_connector_keys import rotate_keys

pytestmark = pytest.mark.asyncio

async def test_credential_rotation(db_session: AsyncSession, company: dict):
    comp_id = uuid.UUID(company["id"])
    
    # Generate two keys
    old_key = Fernet.generate_key().decode('utf-8')
    new_key = Fernet.generate_key().decode('utf-8')
    
    f_old = Fernet(old_key.encode('utf-8'))
    enc_secret = f_old.encrypt(b"my_secret_token").decode('utf-8')
    
    conn = ConnectorConfig(
        company_id=comp_id,
        connector_name="keitaro",
        status="active",
        encrypted_credentials=enc_secret,
        sync_interval_minutes=60
    )
    db_session.add(conn)
    await db_session.commit()
    
    # Rotate
    await rotate_keys(db_session, old_key, new_key, dry_run=False)
    
    # Verify new key decrypts it
    res = await db_session.execute(select(ConnectorConfig).where(ConnectorConfig.id == conn.id))
    updated_conn = res.scalars().first()
    
    f_new = Fernet(new_key.encode('utf-8'))
    decrypted = f_new.decrypt(updated_conn.encrypted_credentials.encode('utf-8')).decode('utf-8')
    assert decrypted == "my_secret_token"
