import asyncio
import logging
from typing import Optional
import redis.asyncio as redis
from sqlalchemy import select, update
from datetime import datetime, timezone
import os

from app.db.session import system_session, tenant_session
from app.db.models.connectors import ConnectorConfig
from app.connectors.keitaro import KeitaroConnector
from app.connectors.base import UnauthorizedError
from app.connectors.credentials import decrypt_secret

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def acquire_lock(lock_key: str, ttl: int = 300) -> bool:
    """Acquires a redis lock with a TTL."""
    return await redis_client.set(lock_key, "locked", nx=True, ex=ttl)

async def release_lock(lock_key: str) -> None:
    """Releases a redis lock."""
    await redis_client.delete(lock_key)

async def sync_connector_instance(company_id: str, connector_id: str) -> None:
    """Runs the sync for a single connector config within tenant context."""
    lock_key = f"sync_lock:{company_id}:{connector_id}"
    
    if not await acquire_lock(lock_key):
        logger.info(f"Sync for connector {connector_id} is already running. Skipping.")
        return

    try:
        async with tenant_session(company_id) as db:
            result = await db.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
            config = result.scalars().first()
            if not config or config.status not in ('active', 'failing'):
                return

            config.last_attempted_sync = datetime.now(timezone.utc)
            await db.commit()
            
            try:
                decrypted = decrypt_secret(config.encrypted_secret)
                
                # Instantiate correct connector class
                if config.connector_name == "keitaro":
                    connector = KeitaroConnector(config, decrypted)
                elif config.connector_name == "binom":
                    from app.connectors.binom import BinomConnector
                    connector = BinomConnector(config, decrypted)
                elif config.connector_name == "voluum":
                    from app.connectors.voluum import VoluumConnector
                    connector = VoluumConnector(config, decrypted)
                elif config.connector_name == "affise":
                    from app.connectors.affise import AffiseConnector
                    connector = AffiseConnector(config, decrypted)
                else:
                    raise ValueError(f"Unknown connector type: {config.connector_name}")

                await connector.sync(db)
                
                # Success
                config.last_successful_sync = datetime.now(timezone.utc)
                config.status = 'active'
                config.retry_count = 0
                await db.commit()
                
            except UnauthorizedError as e:
                logger.error(f"Connector sync unauthorized: {e}")
                config.status = 'unauthorized'
                await db.commit()
            except Exception as e:
                logger.error(f"Connector sync failed: {e}")
                # Failure logic
                config.retry_count += 1
                if config.retry_count > 3:
                    config.status = 'failing'
                await db.commit()
                
    finally:
        await release_lock(lock_key)

async def run_scheduled_syncs():
    """Finds all connectors that need to be synced and launches them."""
    async with system_session() as db:
        # Simplistic: grab all active/failing
        stmt = select(ConnectorConfig).where(ConnectorConfig.status.in_(['active', 'failing']))
        result = await db.execute(stmt)
        configs = result.scalars().all()
        
        tasks = []
        for c in configs:
            # Add simple interval check or just run all for MVP
            tasks.append(sync_connector_instance(str(c.company_id), str(c.id)))
            
        if tasks:
            await asyncio.gather(*tasks)
