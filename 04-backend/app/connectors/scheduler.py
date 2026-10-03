import asyncio
import logging
from typing import Optional
import redis.asyncio as redis
from sqlalchemy import select, update, or_
from datetime import datetime, timezone, timedelta
import os
import uuid

from app.db.session import system_session, tenant_session
from app.db.models.connectors import ConnectorConfig
from app.connectors.registry import CONNECTOR_NAMES, get_connector_class, NON_PRODUCTION_CONNECTORS
from app.connectors.base import UnauthorizedError
from app.connectors.credentials import decrypt_secret

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

SYNC_MAX_CONCURRENCY = int(os.getenv("SYNC_MAX_CONCURRENCY", "5"))

RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

async def acquire_lock(lock_key: str, ttl: int = 300) -> str | None:
    """Acquires a redis lock with a TTL and returns a token."""
    token = str(uuid.uuid4())
    acquired = await redis_client.set(lock_key, token, nx=True, ex=ttl)
    return token if acquired else None

async def release_lock(lock_key: str, token: str) -> None:
    """Releases a redis lock safely using a Lua script."""
    await redis_client.eval(RELEASE_LOCK_SCRIPT, 1, lock_key, token)

async def sync_connector_instance(company_id: str, connector_id: str) -> None:
    """Runs the sync for a single connector config within tenant context."""
    lock_key = f"sync_lock:{company_id}:{connector_id}"
    
    token = await acquire_lock(lock_key)
    if not token:
        logger.info(f"Sync for connector {connector_id} is already running. Skipping.")
        return

    try:
        async with tenant_session(company_id) as db:
            result = await db.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
            config = result.scalars().first()
            if not config or config.status not in ('active', 'failing'):
                return

            now_utc = datetime.now(timezone.utc)
            await db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config.id).values(last_attempted_sync=now_utc))
            await db.commit()
            
        async with tenant_session(company_id) as db:
            result = await db.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
            config = result.scalars().first()

            if not config:
                return

            config_id = config.id
            connector_name = config.connector_name
            sync_interval_minutes = config.sync_interval_minutes
            prev_status = config.status
            prev_retry_count = config.retry_count
            encrypted_secret = config.encrypted_secret

            if connector_name in NON_PRODUCTION_CONNECTORS:
                logger.warning(f"Connector {connector_name} is not production-ready. Pausing.")
                await db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config_id).values(status='paused', next_sync_at=None))
                await db.commit()
                return

            try:
                decrypted = decrypt_secret(encrypted_secret)

                connector_cls = get_connector_class(connector_name)
                if not connector_cls:
                    raise ValueError(f"Unknown connector type: {connector_name}")
                connector = connector_cls(config, decrypted)

                await connector.sync(db)

                # Success
                now_utc = datetime.now(timezone.utc)
                next_sync = now_utc + timedelta(minutes=sync_interval_minutes)
                await db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config_id).values(
                    last_successful_sync=now_utc,
                    status='active',
                    retry_count=0,
                    next_sync_at=next_sync
                ))
                await db.commit()

            except UnauthorizedError as e:
                await db.rollback()
                logger.error(f"Connector sync unauthorized: {type(e).__name__}")
                await db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config_id).values(
                    status='unauthorized',
                    next_sync_at=None
                ))
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error(f"Connector sync failed: {type(e).__name__}")
                new_retry_count = prev_retry_count + 1
                new_status = 'failing' if new_retry_count > 3 else prev_status
                now_utc = datetime.now(timezone.utc)
                retry_interval = max(sync_interval_minutes, 5)
                next_sync = now_utc + timedelta(minutes=retry_interval)
                await db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config_id).values(
                    retry_count=new_retry_count,
                    status=new_status,
                    next_sync_at=next_sync
                ))
                await db.commit()

    finally:
        await release_lock(lock_key, token)

async def _bounded_sync(sem: asyncio.Semaphore, company_id: str, connector_id: str):
    async with sem:
        try:
            await sync_connector_instance(company_id, connector_id)
        except Exception as e:
            logger.error(f"Unhandled exception in sync task for connector {connector_id}: {e}")

async def run_scheduled_syncs():
    """Finds all connectors that need to be synced and launches them."""
    async with system_session() as db:
        now_utc = datetime.now(timezone.utc)
        stmt = select(ConnectorConfig).where(
            ConnectorConfig.status.in_(['active', 'failing']),
            ConnectorConfig.deleted_at.is_(None),
            ConnectorConfig.connector_name.notin_(NON_PRODUCTION_CONNECTORS),
            or_(
                ConnectorConfig.next_sync_at.is_(None),
                ConnectorConfig.next_sync_at <= now_utc
            )
        )
        result = await db.execute(stmt)
        configs = result.scalars().all()
        
        if configs:
            sem = asyncio.Semaphore(SYNC_MAX_CONCURRENCY)
            tasks = [_bounded_sync(sem, str(c.company_id), str(c.id)) for c in configs]
            await asyncio.gather(*tasks, return_exceptions=True)
