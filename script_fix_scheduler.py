with open('04-backend/app/connectors/scheduler.py', 'r') as f:
    content = f.read()

import re

# 1. Module-level import of NON_PRODUCTION_CONNECTORS
content = content.replace('from app.connectors.registry import CONNECTOR_NAMES, get_connector_class', 'from app.connectors.registry import CONNECTOR_NAMES, get_connector_class, NON_PRODUCTION_CONNECTORS')

# 2. Rewrite sync_connector_instance function completely
old_sync = re.search(r'async def sync_connector_instance.*?finally:\n        await release_lock\(lock_key, token\)', content, flags=re.DOTALL).group(0)

new_sync = '''async def sync_connector_instance(company_id: str, connector_id: str) -> None:
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
        await release_lock(lock_key, token)'''

content = content.replace(old_sync, new_sync)

# 3. Fix run_scheduled_syncs (remove the inline import since we added it to module level)
content = content.replace('        from app.connectors.registry import NON_PRODUCTION_CONNECTORS\n', '')

with open('04-backend/app/connectors/scheduler.py', 'w') as f:
    f.write(content)
