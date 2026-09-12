"""
Tests for Stage 2 prep hardening:
- base.py exception security (no response.text)
- FX rate: no silent Decimal("1.0") fallback in binom/voluum/affise
- Date normalization: skip records without stat_date
- Scheduler: next_sync_at filtering and updates
"""
import pytest
import httpx
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
import uuid
from sqlalchemy import select, text
from unittest.mock import AsyncMock, patch, MagicMock

from app.connectors.base import (
    Connector, NormalizedRecord, with_retry,
    ConnectorError, UnauthorizedError, RateLimitError
)
from app.connectors.binom import BinomConnector
from app.connectors.voluum import VoluumConnector
from app.connectors.affise import AffiseConnector
from app.connectors.meta_ads import MetaAdsConnector
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.db.models.users import User
from app.db.models.connectors import ConnectorConfig
from app.db.session import system_session


class DummyConfig:
    def __init__(self, company_id, currency="USD"):
        self.company_id = company_id
        self.settings = {"base_url": "https://test.local", "currency": currency}


# ============================================================
# 1. base.py exception security
# ============================================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_unauthorized_exception_no_response_body(mock_get, monkeypatch):
    """UnauthorizedError message must contain only status code, not response body."""
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "SUPER_SECRET_TOKEN_REFLECTED_IN_BODY"
    mock_get.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=mock_resp
    )

    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret")

    with pytest.raises(UnauthorizedError) as exc_info:
        await connector.fetch_metrics()

    msg = str(exc_info.value)
    assert "SUPER_SECRET" not in msg
    assert "REFLECTED" not in msg
    assert "401" in msg


@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_connector_error_no_response_body(mock_get, monkeypatch):
    """ConnectorError for non-retryable HTTP errors must not contain response body."""
    monkeypatch.setattr("app.connectors.base.asyncio.sleep", AsyncMock())

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = "LEAKED_CREDENTIAL_IN_ERROR_BODY"
    mock_get.side_effect = httpx.HTTPStatusError(
        "400", request=MagicMock(), response=mock_resp
    )

    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret")

    with pytest.raises(ConnectorError) as exc_info:
        await connector.fetch_metrics()

    msg = str(exc_info.value)
    assert "LEAKED_CREDENTIAL" not in msg
    assert "400" in msg


# ============================================================
# 2. FX rate: no silent Decimal("1.0") fallback
# ============================================================

async def _create_company_and_run(db_session, company_id, user_id, note, base_currency="JPY"):
    """Helper: create company + user + campaign_run for FX tests."""
    comp = Company(id=company_id, name=f"FX Test {company_id}", base_currency=base_currency)
    db_session.add(comp)
    await db_session.flush()

    user = User(
        id=user_id, company_id=company_id,
        name="fxtest", email=f"fx_{company_id}@test.com",
        password_hash="hash", role="admin"
    )
    db_session.add(user)
    await db_session.flush()

    run = CampaignRun(
        company_id=company_id,
        buyer_id=user_id,
        started_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        note=note
    )
    db_session.add(run)
    await db_session.commit()
    return run


@pytest.mark.asyncio
async def test_binom_upsert_fx_rate_missing_raises(company_b_fixtures):
    """Binom must raise ValueError when FX rate is not found, not fallback to 1.0."""
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with system_session() as db:
        run = await _create_company_and_run(db, company_id, user_id, "binom_fx_test")

        config = DummyConfig(company_id, currency="GBP")
        connector = BinomConnector(config, "secret")
        raw = [{"camp_id": "binom_fx_test", "date": "2099-01-01", "cost": "50.00", "revenue": "100.00"}]
        normalized = connector.normalize(raw)

        with pytest.raises(ValueError):
            await connector.upsert(db, normalized)

        # Verify no partial CampaignRunStat was created
        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run.id)
        res = await db.execute(stmt)
        assert res.scalars().first() is None


@pytest.mark.asyncio
async def test_voluum_upsert_fx_rate_missing_raises(company_b_fixtures):
    """Voluum must raise ValueError when FX rate is not found."""
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with system_session() as db:
        run = await _create_company_and_run(db, company_id, user_id, "vol_fx_test")

        config = DummyConfig(company_id, currency="GBP")
        connector = VoluumConnector(config, "secret")
        raw = [{"campaignId": "vol_fx_test", "date": "2099-01-01", "cost": "50.00", "revenue": "100.00"}]
        normalized = connector.normalize(raw)

        with pytest.raises(ValueError):
            await connector.upsert(db, normalized)

        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run.id)
        res = await db.execute(stmt)
        assert res.scalars().first() is None


@pytest.mark.asyncio
async def test_affise_upsert_fx_rate_missing_raises(company_b_fixtures):
    """Affise must raise ValueError when FX rate is not found."""
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with system_session() as db:
        run = await _create_company_and_run(db, company_id, user_id, "aff_fx_test")

        config = DummyConfig(company_id, currency="GBP")
        connector = AffiseConnector(config, "secret")
        raw = [{"offer_id": "aff_fx_test", "date": "2099-01-01", "cost": "50.00", "revenue": "100.00"}]
        normalized = connector.normalize(raw)

        with pytest.raises(ValueError):
            await connector.upsert(db, normalized)

        stmt = select(CampaignRunStat).where(CampaignRunStat.campaign_run_id == run.id)
        res = await db.execute(stmt)
        assert res.scalars().first() is None


# ============================================================
# 3. Date normalization: skip records without date
# ============================================================

def test_voluum_normalize_no_date_skips():
    """Voluum must skip records without 'date' field."""
    config = DummyConfig(uuid.uuid4())
    connector = VoluumConnector(config, "secret")
    raw = [{"campaignId": "100", "cost": "10.00", "revenue": "20.00"}]
    normalized = connector.normalize(raw)
    assert len(normalized) == 0


def test_affise_normalize_no_date_skips():
    """Affise must skip records without 'date' field."""
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret")
    raw = [{"offer_id": "100", "cost": "10.00", "revenue": "20.00"}]
    normalized = connector.normalize(raw)
    assert len(normalized) == 0


def test_meta_normalize_no_date_skips():
    """Meta Ads must skip records without 'date_start' field."""
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret")
    raw = [{"campaign_id": "100", "spend": "10.00"}]
    normalized = connector.normalize(raw)
    assert len(normalized) == 0


def test_voluum_normalize_with_date_works():
    """Voluum must normalize records WITH 'date' field correctly."""
    config = DummyConfig(uuid.uuid4())
    connector = VoluumConnector(config, "secret")
    raw = [{"campaignId": "100", "date": "2026-09-01", "cost": "10.00", "revenue": "20.00"}]
    normalized = connector.normalize(raw)
    assert len(normalized) == 1
    assert normalized[0].stat_date == date(2026, 9, 1)


def test_affise_normalize_with_date_works():
    """Affise must normalize records WITH 'date' field correctly."""
    config = DummyConfig(uuid.uuid4())
    connector = AffiseConnector(config, "secret")
    raw = [{"offer_id": "100", "date": "2026-09-01", "cost": "10.00", "revenue": "20.00"}]
    normalized = connector.normalize(raw)
    assert len(normalized) == 1
    assert normalized[0].stat_date == date(2026, 9, 1)


def test_meta_normalize_with_date_works():
    """Meta Ads must normalize records WITH 'date_start' field correctly."""
    config = DummyConfig(uuid.uuid4())
    connector = MetaAdsConnector(config, "secret")
    raw = [{"campaign_id": "100", "date_start": "2026-09-01", "spend": "10.00"}]
    normalized = connector.normalize(raw)
    assert len(normalized) == 1
    assert normalized[0].stat_date == date(2026, 9, 1)


# ============================================================
# 4. Scheduler: next_sync_at filtering
# ============================================================

@pytest.mark.asyncio
async def test_scheduler_due_connector_runs(company_b_fixtures):
    """Connector with next_sync_at in the past should be picked up by run_scheduled_syncs."""
    from app.connectors.scheduler import run_scheduled_syncs
    from app.connectors.credentials import encrypt_secret

    company_id = uuid.uuid4()
    async with system_session() as db:
        comp = Company(id=company_id, name="Sched Due Test", base_currency="USD")
        db.add(comp)
        await db.flush()

        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="binom",
            status="active",
            encrypted_secret=encrypt_secret("fake_secret"),
            next_sync_at=datetime.now(timezone.utc) - timedelta(hours=1),  # past = due
        )
        db.add(conn)
        await db.commit()
        conn_id = conn.id

    # Mock sync_connector_instance to avoid actual connector execution
    with patch("app.connectors.scheduler.sync_connector_instance", new_callable=AsyncMock) as mock_sync:
        await run_scheduled_syncs()
        # Verify the due connector was picked up
        called_ids = [call.args[1] for call in mock_sync.call_args_list]
        assert str(conn_id) in called_ids


@pytest.mark.asyncio
async def test_scheduler_not_due_connector_skipped(company_b_fixtures):
    """Connector with next_sync_at in the future should NOT be picked up."""
    from app.connectors.scheduler import run_scheduled_syncs
    from app.connectors.credentials import encrypt_secret

    company_id = uuid.uuid4()
    async with system_session() as db:
        comp = Company(id=company_id, name="Sched NotDue Test", base_currency="USD")
        db.add(comp)
        await db.flush()

        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="binom",
            status="active",
            encrypted_secret=encrypt_secret("fake_secret"),
            next_sync_at=datetime.now(timezone.utc) + timedelta(hours=1),  # future = not due
        )
        db.add(conn)
        await db.commit()
        conn_id = conn.id

    with patch("app.connectors.scheduler.sync_connector_instance", new_callable=AsyncMock) as mock_sync:
        await run_scheduled_syncs()
        called_ids = [call.args[1] for call in mock_sync.call_args_list]
        assert str(conn_id) not in called_ids


@pytest.mark.asyncio
async def test_scheduler_null_next_sync_runs(company_b_fixtures):
    """Connector with next_sync_at=NULL (first run) should be picked up."""
    from app.connectors.scheduler import run_scheduled_syncs
    from app.connectors.credentials import encrypt_secret

    company_id = uuid.uuid4()
    async with system_session() as db:
        comp = Company(id=company_id, name="Sched Null Test", base_currency="USD")
        db.add(comp)
        await db.flush()

        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="binom",
            status="active",
            encrypted_secret=encrypt_secret("fake_secret"),
            next_sync_at=None,  # NULL = first run, should be picked up
        )
        db.add(conn)
        await db.commit()
        conn_id = conn.id

    with patch("app.connectors.scheduler.sync_connector_instance", new_callable=AsyncMock) as mock_sync:
        await run_scheduled_syncs()
        called_ids = [call.args[1] for call in mock_sync.call_args_list]
        assert str(conn_id) in called_ids


@pytest.mark.asyncio
async def test_scheduler_next_sync_at_updated_on_success(company_b_fixtures):
    """After successful sync, next_sync_at must be set to now + interval. Verified via fresh SELECT."""
    from app.connectors.scheduler import sync_connector_instance
    from app.connectors.credentials import encrypt_secret

    company_id = uuid.uuid4()
    async with system_session() as db:
        comp = Company(id=company_id, name="Sched Success Test", base_currency="USD")
        db.add(comp)
        await db.flush()

        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="meta",
            status="active",
            encrypted_secret=encrypt_secret("fake_secret"),
            sync_interval_minutes=30,
            next_sync_at=None,
        )
        db.add(conn)
        await db.commit()
        conn_id = conn.id

    before_sync = datetime.now(timezone.utc)

    with patch("app.connectors.scheduler.decrypt_secret", return_value="fake"), \
         patch("app.connectors.scheduler.acquire_lock", return_value=True), \
         patch("app.connectors.scheduler.release_lock", new_callable=AsyncMock), \
         patch("app.connectors.base.Connector.sync", new_callable=AsyncMock):
        await sync_connector_instance(str(company_id), str(conn_id))

    # Verify via fresh SELECT in a new session (not ORM identity map)
    async with system_session() as db2:
        stmt = text("SELECT next_sync_at, status, retry_count FROM connector_configs WHERE id = :id")
        res = await db2.execute(stmt, {"id": conn_id})
        row = res.first()
        assert row is not None
        assert row.status == "active"
        assert row.retry_count == 0
        assert row.next_sync_at is not None
        # next_sync_at should be approximately before_sync + 30 minutes
        expected_min = before_sync + timedelta(minutes=29)
        expected_max = before_sync + timedelta(minutes=31)
        assert expected_min <= row.next_sync_at <= expected_max


@pytest.mark.asyncio
async def test_scheduler_unauthorized_sets_null_next_sync(company_b_fixtures):
    """Unauthorized connector should get status=unauthorized and next_sync_at=NULL."""
    from app.connectors.scheduler import sync_connector_instance
    from app.connectors.credentials import encrypt_secret
    from app.connectors.base import UnauthorizedError

    company_id = uuid.uuid4()
    async with system_session() as db:
        comp = Company(id=company_id, name="Sched Unauth Test", base_currency="USD")
        db.add(comp)
        await db.flush()

        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="meta",
            status="active",
            encrypted_secret=encrypt_secret("fake_secret"),
            next_sync_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.add(conn)
        await db.commit()
        conn_id = conn.id

    with patch("app.connectors.scheduler.decrypt_secret", return_value="fake"), \
         patch("app.connectors.scheduler.acquire_lock", return_value=True), \
         patch("app.connectors.scheduler.release_lock", new_callable=AsyncMock), \
         patch("app.connectors.base.Connector.sync", side_effect=UnauthorizedError("Token expired")):
        await sync_connector_instance(str(company_id), str(conn_id))

    async with system_session() as db2:
        stmt = text("SELECT next_sync_at, status FROM connector_configs WHERE id = :id")
        res = await db2.execute(stmt, {"id": conn_id})
        row = res.first()
        assert row.status == "unauthorized"
        assert row.next_sync_at is None


@pytest.mark.asyncio
async def test_scheduler_failure_sets_next_sync_with_retry_interval(company_b_fixtures):
    """Failed sync should set next_sync_at with minimum retry interval."""
    from app.connectors.scheduler import sync_connector_instance
    from app.connectors.credentials import encrypt_secret

    company_id = uuid.uuid4()
    async with system_session() as db:
        comp = Company(id=company_id, name="Sched Fail Test", base_currency="USD")
        db.add(comp)
        await db.flush()

        conn = ConnectorConfig(
            company_id=company_id,
            connector_name="meta",
            status="active",
            encrypted_secret=encrypt_secret("fake_secret"),
            sync_interval_minutes=60,
            next_sync_at=None,
        )
        db.add(conn)
        await db.commit()
        conn_id = conn.id

    before_sync = datetime.now(timezone.utc)

    with patch("app.connectors.scheduler.decrypt_secret", return_value="fake"), \
         patch("app.connectors.scheduler.acquire_lock", return_value=True), \
         patch("app.connectors.scheduler.release_lock", new_callable=AsyncMock), \
         patch("app.connectors.base.Connector.sync", side_effect=RuntimeError("network error")):
        await sync_connector_instance(str(company_id), str(conn_id))

    async with system_session() as db2:
        stmt = text("SELECT next_sync_at, status, retry_count FROM connector_configs WHERE id = :id")
        res = await db2.execute(stmt, {"id": conn_id})
        row = res.first()
        assert row.retry_count == 1
        assert row.next_sync_at is not None
        # next_sync_at should be at least before_sync + max(60, 5) minutes
        expected_min = before_sync + timedelta(minutes=59)
        assert row.next_sync_at >= expected_min
