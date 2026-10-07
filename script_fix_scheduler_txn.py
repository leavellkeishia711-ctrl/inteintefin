import re

with open('04-backend/app/connectors/scheduler.py', 'r') as f:
    content = f.read()

old_logic = '''            try:
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
                await db.commit()'''

new_logic = '''            sync_error_type = None

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
                sync_error_type = 'unauthorized'
                logger.error(f"Connector sync unauthorized: {type(e).__name__}")
            except Exception as e:
                await db.rollback()
                sync_error_type = 'failed'
                logger.error(f"Connector sync failed: {type(e).__name__}")

        if sync_error_type:
            async with tenant_session(company_id) as err_db:
                if sync_error_type == 'unauthorized':
                    await err_db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config_id).values(
                        status='unauthorized',
                        next_sync_at=None
                    ))
                    await err_db.commit()
                else:
                    new_retry_count = prev_retry_count + 1
                    new_status = 'failing' if new_retry_count > 3 else prev_status
                    now_utc = datetime.now(timezone.utc)
                    retry_interval = max(sync_interval_minutes, 5)
                    next_sync = now_utc + timedelta(minutes=retry_interval)
                    await err_db.execute(update(ConnectorConfig).where(ConnectorConfig.id == config_id).values(
                        retry_count=new_retry_count,
                        status=new_status,
                        next_sync_at=next_sync
                    ))
                    await err_db.commit()'''

content = content.replace(old_logic, new_logic)

with open('04-backend/app/connectors/scheduler.py', 'w') as f:
    f.write(content)
