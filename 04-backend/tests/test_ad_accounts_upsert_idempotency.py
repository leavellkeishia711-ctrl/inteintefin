import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.campaigns import AdAccount
from app.db.models.connectors import ConnectorConfig
from app.connectors.base import NormalizedAdAccount, Connector
import uuid

pytestmark = pytest.mark.asyncio

class DummyConnector(Connector):
    async def fetch(self):
        return []
    def normalize(self, data):
        return []
    async def upsert(self, session, data):
        pass
    async def test_connection(self):
        return True

async def test_upsert_idempotency(db_session: AsyncSession, company: dict):
    comp_id = uuid.UUID(company["id"])
    
    config = ConnectorConfig(
        company_id=comp_id,
        connector_name="dummy",
        status="active",
        encrypted_secret="enc"
    )
    db_session.add(config)
    await db_session.commit()
    
    conn = DummyConnector(config)
    
    acc = NormalizedAdAccount(
        platform="tiktok",
        external_account_id="12345",
        name="TT Acc",
        status="active"
    )
    
    # First upsert
    await conn.upsert_ad_accounts(db_session, [acc])
    await db_session.commit()
    
    res = await db_session.execute(select(AdAccount).where(AdAccount.platform == "tiktok"))
    accounts = res.scalars().all()
    assert len(accounts) == 1
    
    # Second upsert (update name doesn't exist, wait, upsert only updates status?)
    acc.status = "paused"
    await conn.upsert_ad_accounts(db_session, [acc])
    await db_session.commit()
    
    res = await db_session.execute(select(AdAccount).where(AdAccount.platform == "tiktok"))
    accounts = res.scalars().all()
    assert len(accounts) == 1
    assert accounts[0].status == "paused"
