import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
import uuid
import redis.asyncio as redis

from app.core.deps import get_db, require_roles
from app.db.models.connectors import ConnectorConfig
from app.connectors.credentials import encrypt_secret
from app.connectors.registry import CONNECTOR_NAMES, get_connector_class
from app.connectors.base import UnauthorizedError
from app.services.audit import record_user_audit
from app.workers.tasks import manual_sync_connector_task

router = APIRouter()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class ConnectorCreate(BaseModel):
    connector_name: str
    secret: str
    sync_interval_minutes: int = 60

class ConnectorUpdate(BaseModel):
    secret: str | None = None
    sync_interval_minutes: int | None = None
    status: str | None = None

class ConnectorResponse(BaseModel):
    id: uuid.UUID
    connector_name: str
    status: str
    sync_interval_minutes: int
    last_attempted_sync: datetime | None
    last_successful_sync: datetime | None

    class Config:
        from_attributes = True

@router.post("/", response_model=ConnectorResponse, status_code=201)
async def create_connector(
    config_in: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner"))
):
    if config_in.connector_name not in CONNECTOR_NAMES:
        raise HTTPException(status_code=422, detail=f"Unknown connector type. Allowed: {list(CONNECTOR_NAMES)}")

    stmt = select(ConnectorConfig).where(
        ConnectorConfig.connector_name == config_in.connector_name,
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    )
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Connector already exists")

    encrypted = encrypt_secret(config_in.secret)
    new_config = ConnectorConfig(
        company_id=user.company_id,
        connector_name=config_in.connector_name,
        encrypted_secret=encrypted,
        sync_interval_minutes=config_in.sync_interval_minutes
    )
    db.add(new_config)
    await db.flush()
    await db.refresh(new_config)
    return new_config

@router.get("/", response_model=List[ConnectorResponse])
async def list_connectors(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner", "cfo", "member"))
):
    res = await db.execute(select(ConnectorConfig).where(
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    ))
    return res.scalars().all()

@router.patch("/{connector_id}", response_model=ConnectorResponse)
async def update_connector(
    connector_id: uuid.UUID,
    config_in: ConnectorUpdate,
    validate: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner"))
):
    res = await db.execute(select(ConnectorConfig).where(
        ConnectorConfig.id == connector_id,
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    ))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    if config_in.secret is not None:
        if validate:
            if config.connector_name not in CONNECTOR_NAMES:
                raise HTTPException(status_code=422, detail=f"Unknown connector type. Allowed: {list(CONNECTOR_NAMES)}")
            connector_cls = get_connector_class(config.connector_name)
            
            # Use a dummy config just for validation
            dummy_config = ConnectorConfig(
                company_id=config.company_id,
                connector_name=config.connector_name,
                sync_interval_minutes=config.sync_interval_minutes
            )
            connector = connector_cls(dummy_config, config_in.secret)
            try:
                ok = await connector.test_connection()
                if not ok:
                    raise HTTPException(status_code=502, detail="Connection test failed")
            except UnauthorizedError:
                raise HTTPException(status_code=400, detail="Invalid credentials")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=502, detail="Connection test failed")
                    
        config.encrypted_secret = encrypt_secret(config_in.secret)
        if config.status in ('unauthorized', 'failing'):
            config.status = 'active'
        config.retry_count = 0
        config.next_sync_at = datetime.now(timezone.utc)
        
        await record_user_audit(
            session=db,
            user=user,
            entity_type="connector",
            entity_id=config.id,
            action="connector.credentials_rotated",
            old_state={},
            new_state={"connector_id": str(config.id), "connector_name": config.connector_name}
        )

    if config_in.sync_interval_minutes is not None:
        config.sync_interval_minutes = config_in.sync_interval_minutes
    if config_in.status is not None:
        if config_in.status not in ["active", "paused"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        config.status = config_in.status
        
    await db.flush()
    await db.refresh(config)
    return config

@router.delete("/{connector_id}", status_code=204)
async def delete_connector(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner"))
):
    res = await db.execute(select(ConnectorConfig).where(
        ConnectorConfig.id == connector_id,
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    ))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    config.deleted_at = datetime.now(timezone.utc)
    config.status = "paused"
    await db.flush()
    return None

@router.post("/{connector_id}/sync", status_code=202)
async def manual_sync(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("owner", "cfo"))
):
    res = await db.execute(select(ConnectorConfig).where(
        ConnectorConfig.id == connector_id,
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    ))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    # Rate limit check first (read-only)
    rl_key = f"rl:manual_sync:{config.id}"
    if await redis_client.exists(rl_key):
        raise HTTPException(status_code=429, detail="Too many sync requests")
        
    config.last_attempted_sync = datetime.now(timezone.utc)
    await db.flush()
    
    # Set rate limit after successful db flush
    await redis_client.set(rl_key, "1", ex=60)
    
    # Spawn task via celery in threadpool
    task = await run_in_threadpool(manual_sync_connector_task.delay, str(user.company_id), str(config.id))
    
    return {"status": "sync_started", "task_id": task.id}
