from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

from app.api.deps import get_db, require_roles
from app.db.models.connectors import ConnectorConfig
from app.connectors.credentials import encrypt_secret
from app.connectors.scheduler import sync_connector_instance

router = APIRouter()

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

@router.post("/", response_model=ConnectorResponse)
async def create_connector(
    config_in: ConnectorCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["owner"]))
):
    stmt = select(ConnectorConfig).where(
        ConnectorConfig.connector_name == config_in.connector_name,
        ConnectorConfig.company_id == user.company_id
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
    await db.commit()
    await db.refresh(new_config)
    return new_config

@router.get("/", response_model=List[ConnectorResponse])
async def list_connectors(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["owner", "cfo", "member"]))
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
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["owner"]))
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
        config.encrypted_secret = encrypt_secret(config_in.secret)
    if config_in.sync_interval_minutes is not None:
        config.sync_interval_minutes = config_in.sync_interval_minutes
    if config_in.status is not None:
        if config_in.status not in ["active", "paused"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        config.status = config_in.status
        
    await db.commit()
    await db.refresh(config)
    return config

@router.delete("/{connector_id}", status_code=204)
async def delete_connector(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["owner"]))
):
    res = await db.execute(select(ConnectorConfig).where(
        ConnectorConfig.id == connector_id,
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    ))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    from datetime import datetime, timezone
    config.deleted_at = datetime.now(timezone.utc)
    config.status = "paused"
    await db.commit()
    return None

@router.post("/{connector_id}/sync")
async def manual_sync(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["owner", "cfo"]))
):
    res = await db.execute(select(ConnectorConfig).where(
        ConnectorConfig.id == connector_id,
        ConnectorConfig.company_id == user.company_id,
        ConnectorConfig.deleted_at.is_(None)
    ))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    import asyncio
    asyncio.create_task(sync_connector_instance(str(user.company_id), str(config.id)))
    
    return {"status": "sync_started"}
