import asyncio
from datetime import date
from decimal import Decimal
import pytest
import uuid
from sqlalchemy import select, text
from app.db.models.campaigns import CampaignRun, CampaignRunStat
from app.connectors.base import NormalizedRecord
from app.db.session import async_session_maker

from app.db.models.campaigns import CampaignRun, ExternalCampaignMapping
from datetime import datetime, timezone

async def create_dummy_run(client, company_id):
    me = await client.get("/api/v1/auth/me")
    user_id = uuid.UUID(me.json()["id"])
    run_id = uuid.uuid4()
    async with async_session_maker() as session:
        run = CampaignRun(
            id=run_id,
            company_id=company_id,
            buyer_id=user_id,
            started_at=datetime.now(timezone.utc)
        )
        session.add(run)
        await session.commit()
    return run_id


@pytest.fixture
async def company_id_fixture():
    return uuid.uuid4()

@pytest.mark.asyncio
async def test_upsert_race_atomic_insert_or_update(client_a):
    """
    UPSERT race: two tasks simultaneously attempt INSERT with same (company_id, campaign_run_id, stat_date, source, external_id).
    Expected: exactly one row in DB, no duplicate key error, updated values reflect last write (deterministic due to ON CONFLICT DO UPDATE).
    """
    me = await client_a.get("/api/v1/auth/me")
    company_id = uuid.UUID(me.json()["company_id"])
    campaign_run_id = await create_dummy_run(client_a, company_id)
    stat_date = date(2026, 9, 1)
    source = "binom"
    external_id = "ext_100"
    
    normalized_v1 = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("100.00"),
        revenue=Decimal("200.00"),
        currency="USD",
        source=source,
        
    )
    
    normalized_v2 = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("150.00"),
        revenue=Decimal("250.00"),
        currency="USD",
        source=source,
        
    )
    
    results = []
    errors = []
    
    async def insert_task(normalized, version):
        try:
            async with async_session_maker() as session:
                await CampaignRunStat.upsert_campaign_run_stat_atomic(
                    session=session,
                    company_id=company_id,
                    campaign_run_id=campaign_run_id,
                    stat_date=stat_date,
                    source=source,
                    
                    normalized_record=normalized,
                    connector_name="BinomConnector",
                    fx_rate_to_base=Decimal("1.0"),
                    currency="USD"
                )
                await session.commit()
                results.append((version, "success"))
        except Exception as e:
            errors.append((version, str(e)))

    # Simultaneous insert race
    await asyncio.gather(
        insert_task(normalized_v1, "v1"),
        insert_task(normalized_v2, "v2")
    )
    
    # Verify: no errors
    assert len(errors) == 0, f"Race condition caused errors: {errors}"
    
    # Verify: exactly 1 row in DB
    async with async_session_maker() as session:
        stmt = select(CampaignRunStat).filter_by(
            company_id=company_id,
            campaign_run_id=campaign_run_id,
            stat_date=stat_date,
            source=source,
            external_id=external_id
        )
        res = await session.execute(stmt)
        rows = res.scalars().all()
        assert len(rows) == 1, f"Expected 1 row, found {len(rows)} (upsert race not atomic)"
        
        row = rows[0]
        assert row is not None
        assert row.spend in [Decimal("100.00"), Decimal("150.00")], \
            f"Unexpected spend value: {row.spend}"

@pytest.mark.asyncio
async def test_upsert_idempotent_multiple_calls(client_a):
    """
    Call upsert_campaign_run_stat_atomic 5 times with identical inputs.
    Expected: exactly 1 row, all metrics identical to input, no errors.
    """
    me = await client_a.get("/api/v1/auth/me")
    company_id = uuid.UUID(me.json()["company_id"])
    campaign_run_id = await create_dummy_run(client_a, company_id)
    stat_date = date(2026, 9, 2)
    source = "voluum"
    external_id = "ext_200"
    
    normalized = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("50.00"),
        revenue=Decimal("100.00"),
        currency="EUR",
        source=source,
        
    )
    
    async with async_session_maker() as session:
        for i in range(5):
            result = await CampaignRunStat.upsert_campaign_run_stat_atomic(
                session=session,
                company_id=company_id,
                campaign_run_id=campaign_run_id,
                stat_date=stat_date,
                source=source,
                
                normalized_record=normalized,
                connector_name="VoluumConnector",
                fx_rate_to_base=Decimal("1.1"),
                currency="EUR"
            )
            assert result.spend == Decimal("50.00")
            assert result.revenue == Decimal("100.00")
        await session.commit()
    
    # Verify: exactly 1 row
    async with async_session_maker() as session:
        stmt = select(CampaignRunStat).filter_by(
            company_id=company_id,
            campaign_run_id=campaign_run_id,
        )
        res = await session.execute(stmt)
        count = len(res.scalars().all())
        assert count == 1, f"Expected 1 row after 5 idempotent upserts, found {count}"

@pytest.mark.asyncio
async def test_upsert_soft_delete_respects_index_predicate(client_a):
    """
    Insert row A, mark as deleted_at=now(), then upsert same keys with new data.
    Expected: new row inserted (not updated), both A (deleted) and B (active) in DB.
    """
    me = await client_a.get("/api/v1/auth/me")
    company_id = uuid.UUID(me.json()["company_id"])
    campaign_run_id = await create_dummy_run(client_a, company_id)
    stat_date = date(2026, 9, 3)
    source = "affise"
    external_id = "ext_300"
    
    normalized_v1 = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("75.00"),
        revenue=Decimal("150.00"),
        currency="GBP",
        source=source,
        
    )
    
    normalized_v2 = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("80.00"),
        revenue=Decimal("160.00"),
        currency="GBP",
        source=source,
        
    )
    
    async with async_session_maker() as session:
        # Insert row A
        row_a = await CampaignRunStat.upsert_campaign_run_stat_atomic(
            session=session,
            company_id=company_id,
            campaign_run_id=campaign_run_id,
            stat_date=stat_date,
            source=source,
            
            normalized_record=normalized_v1,
            connector_name="AffiseConnector",
            fx_rate_to_base=Decimal("1.2"),
            currency="GBP"
        )
        row_a_id = row_a.id
        await session.commit()
        
        # Mark as deleted
        await session.execute(
            text("UPDATE campaign_run_stats SET deleted_at = now() WHERE id = :id"),
            {"id": str(row_a_id)}
        )
        await session.commit()
        
        # Upsert same keys with new data
        row_b = await CampaignRunStat.upsert_campaign_run_stat_atomic(
            session=session,
            company_id=company_id,
            campaign_run_id=campaign_run_id,
            stat_date=stat_date,
            source=source,
            
            normalized_record=normalized_v2,
            connector_name="AffiseConnector",
            fx_rate_to_base=Decimal("1.2"),
            currency="GBP"
        )
        row_b_id = row_b.id
        await session.commit()
        
    async with async_session_maker() as session:
        stmt = select(CampaignRunStat).filter_by(
            company_id=company_id,
            campaign_run_id=campaign_run_id,
        )
        res = await session.execute(stmt)
        rows = res.scalars().all()
        assert len(rows) == 2, f"Expected 2 rows (A deleted + B active), found {len(rows)}"
        
        assert row_a_id != row_b_id, "Expected new row after soft delete, got update"
        
        deleted_row = next(r for r in rows if r.id == row_a_id)
        assert deleted_row.deleted_at is not None, "Row A should be deleted"
        
        active_row = next(r for r in rows if r.id == row_b_id)
        assert active_row.deleted_at is None, "Row B should be active"
        assert active_row.spend == Decimal("80.00"), "Row B should have new data"

@pytest.mark.asyncio
async def test_upsert_tenant_isolation_race(client_a, client_b):
    """
    Company A and Company B attempt concurrent upsert with same keys.
    Expected: 2 separate rows in DB, no cross-tenant contamination.
    """
    me_a = await client_a.get("/api/v1/auth/me")
    company_a = uuid.UUID(me_a.json()["company_id"])
    me_b = await client_b.get("/api/v1/auth/me")
    company_b = uuid.UUID(me_b.json()["company_id"])
    
    campaign_run_id_a = await create_dummy_run(client_a, company_a)
    campaign_run_id_b = await create_dummy_run(client_b, company_b)
    
    stat_date = date(2026, 9, 4)
    source = "meta_ads"
    external_id = "ext_400"
    
    normalized_a = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("200.00"),
        revenue=Decimal("400.00"),
        currency="USD",
        source=source,
        
    )
    
    normalized_b = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("300.00"),
        revenue=Decimal("600.00"),
        currency="USD",
        source=source,
        
    )
    
    errors = []
    
    async def insert_for_company(company_id, campaign_run_id, normalized, company_name):
        try:
            async with async_session_maker() as session:
                await CampaignRunStat.upsert_campaign_run_stat_atomic(
                    session=session,
                    company_id=company_id,
                    campaign_run_id=campaign_run_id,
                    stat_date=stat_date,
                    source=source,
                    
                    normalized_record=normalized,
                    connector_name="MetaAdsConnector",
                    fx_rate_to_base=Decimal("1.0"),
                    currency="USD"
                )
                await session.commit()
        except Exception as e:
            errors.append((company_name, str(e)))

    # Concurrent inserts for A and B
    await asyncio.gather(
        insert_for_company(company_a, campaign_run_id_a, normalized_a, "A"),
        insert_for_company(company_b, campaign_run_id_b, normalized_b, "B")
    )
    
    assert len(errors) == 0, f"Errors during concurrent tenant inserts: {errors}"
    
    # Verify: 2 rows, separate per company
    async with async_session_maker() as session:
        stmt_a = select(CampaignRunStat).filter_by(
            company_id=company_a,
            campaign_run_id=campaign_run_id_a,
            stat_date=stat_date,
        )
        row_a = (await session.execute(stmt_a)).scalars().first()
        
        stmt_b = select(CampaignRunStat).filter_by(
            company_id=company_b,
            campaign_run_id=campaign_run_id_b,
            stat_date=stat_date,
        )
        row_b = (await session.execute(stmt_b)).scalars().first()
        
        assert row_a is not None, "Company A row not inserted"
        assert row_b is not None, "Company B row not inserted"
        assert row_a.spend == Decimal("200.00"), "Company A data incorrect"
        assert row_b.spend == Decimal("300.00"), "Company B data incorrect"

@pytest.mark.asyncio
async def test_upsert_all_fields_updated_correctly(client_a):
    """
    Insert row with v1 data, then upsert same keys with v2 data.
    Expected: row is updated, ALL mutable fields reflect v2 data, updated_at refreshed.
    """
    me = await client_a.get("/api/v1/auth/me")
    company_id = uuid.UUID(me.json()["company_id"])
    campaign_run_id = await create_dummy_run(client_a, company_id)
    stat_date = date(2026, 9, 5)
    source = "binom"
    external_id = "ext_500"
    
    normalized_v1 = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("10.00"),
        revenue=Decimal("20.00"),
        currency="USD",
        source=source,
        
    )
    
    normalized_v2 = NormalizedRecord(
        stat_date=stat_date,
        spend=Decimal("15.00"),
        revenue=Decimal("25.00"),
        currency="EUR",
        source=source,
        
    )
    
    async with async_session_maker() as session:
        # Insert v1
        row_v1 = await CampaignRunStat.upsert_campaign_run_stat_atomic(
            session=session,
            company_id=company_id,
            campaign_run_id=campaign_run_id,
            stat_date=stat_date,
            source=source,
            
            normalized_record=normalized_v1,
            connector_name="BinomConnector",
            fx_rate_to_base=Decimal("1.0"),
            currency="USD"
        )
        row_id = row_v1.id
        created_at_v1 = row_v1.created_at
        updated_at_v1 = row_v1.updated_at
        await session.commit()
        
        # Small delay
        import asyncio
        await asyncio.sleep(0.1)
        
        # Upsert v2
        row_v2 = await CampaignRunStat.upsert_campaign_run_stat_atomic(
            session=session,
            company_id=company_id,
            campaign_run_id=campaign_run_id,
            stat_date=stat_date,
            source=source,
            
            normalized_record=normalized_v2,
            connector_name="BinomConnector",
            fx_rate_to_base=Decimal("1.0"),
            currency="USD"
        )
        await session.commit()
        
        assert row_v2.id == row_id, "Expected same row ID after upsert"
        assert row_v2.spend == Decimal("15.00"), f"spend not updated: {row_v2.spend}"
        assert row_v2.revenue == Decimal("25.00"), f"revenue not updated: {row_v2.revenue}"
        # NOTE: impressions, clicks, conversions omitted from verification because they are not present in CampaignRunStat model
        assert row_v2.created_at == created_at_v1, "created_at should not change"
        assert row_v2.updated_at > updated_at_v1, "updated_at should be refreshed"
