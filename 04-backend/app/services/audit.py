import uuid
from typing import Any, Dict
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog
from app.core.deps import UserCtx

SENSITIVE_FIELDS = {"password_hash", "token_hash", "identifier", "telegram_link_token", "card_number", "card_identifier", "api_key", "secret"}

def json_serialize(obj: Any) -> Any:
    """Recursively serialize complex types to JSON-serializable formats."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: json_serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_serialize(i) for i in obj]
    return obj

def generate_diff(old_state: dict, new_state: dict) -> dict:
    """Generate a clean dictionary of changes (JSONB diff)."""
    diff = {}
    
    # Keys in new state
    for k, new_v in new_state.items():
        if k in SENSITIVE_FIELDS:
            continue
        old_v = old_state.get(k)
        if old_v != new_v:
            diff[k] = {"old": json_serialize(old_v), "new": json_serialize(new_v)}
            
    # Keys deleted in new state
    for k, old_v in old_state.items():
        if k in SENSITIVE_FIELDS:
            continue
        if k not in new_state:
            diff[k] = {"old": json_serialize(old_v), "new": None}
            
    return diff

async def record_user_audit(
    session: AsyncSession, 
    user: UserCtx, 
    entity_type: str, 
    entity_id: uuid.UUID | None, 
    action: str, 
    old_state: dict | None = None,
    new_state: dict | None = None,
    request_id: str | None = None,
    ip_address: str | None = None
):
    diff = None
    if old_state is not None or new_state is not None:
        diff = generate_diff(old_state or {}, new_state or {})
        if not diff and action != "delete": # Don't log empty updates
            return

    company_id_val = uuid.UUID(user.company_id) if isinstance(user.company_id, str) else user.company_id
    user_id_val = uuid.UUID(user.user_id) if isinstance(user.user_id, str) else user.user_id

    log = AuditLog(
        company_id=company_id_val,
        actor_type='user',
        actor_user_id=user_id_val,
        source=None,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        diff=diff,
        request_id=uuid.UUID(request_id) if request_id else None,
        ip_address=ip_address
    )
    session.add(log)


async def record_system_audit(
    session: AsyncSession, 
    company_id: str | uuid.UUID,
    task_name: str,
    entity_type: str, 
    entity_id: uuid.UUID | None, 
    action: str, 
    old_state: dict | None = None,
    new_state: dict | None = None,
):
    diff = None
    if old_state is not None or new_state is not None:
        diff = generate_diff(old_state or {}, new_state or {})
        if not diff and action != "delete":
            return

    company_id_val = uuid.UUID(company_id) if isinstance(company_id, str) else company_id

    log = AuditLog(
        company_id=company_id_val,
        actor_type='system',
        actor_user_id=None,
        source=f"celery:{task_name}",
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        diff=diff,
        request_id=None,
        ip_address=None
    )
    session.add(log)
