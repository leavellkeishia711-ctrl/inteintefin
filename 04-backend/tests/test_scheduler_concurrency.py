import pytest
import asyncio
from unittest.mock import AsyncMock
from app.connectors import scheduler
from app.db.models.connectors import ConnectorConfig
from app.db.models import Company
from sqlalchemy import select
from datetime import datetime, timezone, timedelta
import uuid

@pytest.mark.asyncio
async def test_scheduler_max_concurrency(system_session, monkeypatch):
    # Setup test companies and configs
    company = Company(name="Test Co")
    system_session.add(company)
    await system_session.commit()
    await system_session.refresh(company)
    
    configs = []
    now_utc = datetime.now(timezone.utc)
    for i in range(20):
        c = ConnectorConfig(
            company_id=company.id,
            connector_name="meta",
            encrypted_secret="enc1",
            status="active",
            next_sync_at=now_utc - timedelta(minutes=1)
        )
        configs.append(c)
        system_session.add(c)
    await system_session.commit()

    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    
    async def mock_sync(cid, conn_id):
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            if in_flight > max_in_flight:
                max_in_flight = in_flight
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
            
    monkeypatch.setattr(scheduler, "sync_connector_instance", mock_sync)
    monkeypatch.setattr(scheduler, "SYNC_MAX_CONCURRENCY", 5)
    
    await scheduler.run_scheduled_syncs()
    
    assert max_in_flight <= 5
    assert max_in_flight > 0

@pytest.mark.asyncio
async def test_scheduler_batch_continues_on_error(system_session, monkeypatch):
    company = Company(name="Test Co")
    system_session.add(company)
    await system_session.commit()
    await system_session.refresh(company)
    
    configs = []
    now_utc = datetime.now(timezone.utc)
    for i in range(20):
        c = ConnectorConfig(
            company_id=company.id,
            connector_name="meta",
            encrypted_secret="enc1",
            status="active",
            next_sync_at=now_utc - timedelta(minutes=1)
        )
        configs.append(c)
        system_session.add(c)
    await system_session.commit()

    called = 0
    
    async def mock_sync(cid, conn_id):
        nonlocal called
        called += 1
        if called == 1:
            raise Exception("First task fails")
            
    monkeypatch.setattr(scheduler, "sync_connector_instance", mock_sync)
    monkeypatch.setattr(scheduler, "SYNC_MAX_CONCURRENCY", 5)
    
    # Should not raise exception
    await scheduler.run_scheduled_syncs()
    
    assert called == 20

@pytest.mark.asyncio
async def test_safe_redis_lock_release(monkeypatch):
    # Setup mock redis
    class MockRedis:
        def __init__(self):
            self.store = {}
            
        async def set(self, k, v, nx=False, ex=None):
            if nx and k in self.store:
                return False
            self.store[k] = v
            return True
            
        async def eval(self, script, numkeys, key, arg):
            # simulate lua
            if self.store.get(key) == arg:
                del self.store[key]
                return 1
            return 0
            
    mock_redis = MockRedis()
    monkeypatch.setattr(scheduler, "redis_client", mock_redis)
    
    token = await scheduler.acquire_lock("test_key")
    assert token is not None
    assert mock_redis.store["test_key"] == token
    
    # attempt release with wrong token
    await scheduler.release_lock("test_key", "wrong_token")
    assert "test_key" in mock_redis.store # lock not released
    
    # attempt release with right token
    await scheduler.release_lock("test_key", token)
    assert "test_key" not in mock_redis.store # lock released
