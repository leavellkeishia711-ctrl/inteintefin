import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.db.models.connectors import ConnectorConfig
from app.scripts.rotate_connector_keys import rotate_keys

pytestmark = pytest.mark.asyncio

async def test_credential_rotation_rollback(db_session: AsyncSession, company: dict):
    comp_id = uuid.UUID(company["id"])
    
    # Old key but we will provide a WRONG old key
    old_key = Fernet.generate_key().decode('utf-8')
    wrong_old_key = Fernet.generate_key().decode('utf-8')
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
    
    # Rotate should fail
    with pytest.raises(Exception):
        await rotate_keys(db_session, wrong_old_key, new_key, dry_run=False)
        
    # Verify rollback - old key still decrypts it
    res = await db_session.execute(select(ConnectorConfig).where(ConnectorConfig.id == conn.id))
    updated_conn = res.scalars().first()
    
    decrypted = f_old.decrypt(updated_conn.encrypted_credentials.encode('utf-8')).decode('utf-8')
    assert decrypted == "my_secret_token"
