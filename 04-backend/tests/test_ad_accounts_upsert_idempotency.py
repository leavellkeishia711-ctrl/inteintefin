import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.campaigns import AdAccount
from app.connectors.base import NormalizedAdAccount, upsert_ad_accounts
import uuid

pytestmark = pytest.mark.asyncio

async def test_upsert_idempotency(db_session: AsyncSession, company: dict):
    comp_id = uuid.UUID(company["id"])
    
    acc = NormalizedAdAccount(
        platform="tiktok",
        external_account_id="12345",
        name="TT Acc",
        status="active"
    )
    
    # First upsert
    await upsert_ad_accounts(db_session, comp_id, [acc])
    await db_session.commit()
    
    res = await db_session.execute(select(AdAccount).where(AdAccount.platform == "tiktok"))
    accounts = res.scalars().all()
    assert len(accounts) == 1
    
    # Second upsert (update name)
    acc.name = "TT Acc Updated"
    await upsert_ad_accounts(db_session, comp_id, [acc])
    await db_session.commit()
    
    res = await db_session.execute(select(AdAccount).where(AdAccount.platform == "tiktok"))
    accounts = res.scalars().all()
    assert len(accounts) == 1
    assert accounts[0].name == "TT Acc Updated"
