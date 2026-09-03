from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    user=Depends(require_roles(["admin", "owner"]))
):
    stmt = select(ConnectorConfig).where(ConnectorConfig.connector_name == config_in.connector_name)
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
    user=Depends(require_roles(["admin", "owner", "buyer"]))
):
    res = await db.execute(select(ConnectorConfig))
    return res.scalars().all()

@router.post("/{connector_id}/sync")
async def manual_sync(
    connector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["admin", "owner"]))
):
    res = await db.execute(select(ConnectorConfig).where(ConnectorConfig.id == connector_id))
    config = res.scalars().first()
    if not config:
        raise HTTPException(status_code=404, detail="Connector not found")
        
    import asyncio
    # Fire and forget
    asyncio.create_task(sync_connector_instance(str(user.company_id), str(config.id)))
    
    return {"status": "sync_started"}
