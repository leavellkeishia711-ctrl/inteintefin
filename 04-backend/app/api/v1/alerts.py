from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db_session
from app.core.deps import get_tenant_session, get_current_user, UserCtx
from app.services.alerts import get_active_alerts
from app.db.models import Alert
from datetime import datetime, timezone
import uuid

router = APIRouter()

@router.get("/")
async def list_alerts(
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    alerts = await get_active_alerts(db, uuid.UUID(user.company_id))
    return {
        "items": [
            {
                "id": str(alert.id),
                "type": alert.type,
                "risk_level": alert.risk_level,
                "message": alert.message,
                "triggered_at": str(alert.triggered_at),
                "cooldown_until": str(alert.cooldown_until) if alert.cooldown_until else None,
            }
            for alert in alerts
        ]
    }

@router.post("/{id}/acknowledge")
async def acknowledge_alert(
    id: str,
    db: AsyncSession = Depends(get_tenant_session),
    user: UserCtx = Depends(get_current_user)
):
    alert = await db.get(Alert, uuid.UUID(id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if alert.acknowledged_at:
        return {"status": "already_acknowledged"}
        
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = uuid.UUID(user.user_id)
    
    await db.flush()
    return {"status": "acknowledged"}
