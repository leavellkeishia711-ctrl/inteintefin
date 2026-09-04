import pytest
import uuid
from app.db.session import system_session
from sqlalchemy import select
from cryptography.fernet import Fernet
from app.db.models.connectors import ConnectorConfig
from app.scripts.rotate_connector_keys import rotate_keys

pytestmark = pytest.mark.asyncio

async def test_credential_rotation_rollback(company_b_fixtures):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    
    async with system_session() as db_session:
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
            encrypted_secret=enc_secret,
            sync_interval_minutes=60
        )
        db_session.add(conn)
        await db_session.commit()
        conn_id = conn_id
        
        # Rotate should fail
        with pytest.raises(Exception):
            await rotate_keys(wrong_old_key, new_key, db=db_session, dry_run=False, company_id=comp_id)
            
        # Verify rollback - old key still decrypts it
        res = await db_session.execute(select(ConnectorConfig.encrypted_secret).where(ConnectorConfig.id == conn_id))
        secret_val = res.scalar()
        decrypted = f_old.decrypt(secret_val.encode('utf-8')).decode('utf-8')
        assert decrypted == "my_secret_token"
