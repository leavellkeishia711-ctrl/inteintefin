import pytest
import uuid
from decimal import Decimal
from datetime import datetime, date
from app.services.audit import generate_diff, record_user_audit, record_system_audit
from app.core.deps import UserCtx
from app.db.models.system import AuditLog
from sqlalchemy import select

def test_generate_diff_omits_sensitive_fields():
    old = {"password_hash": "abc", "identifier": "1234", "name": "John"}
    new = {"password_hash": "def", "identifier": "5678", "name": "Jane"}
    
    diff = generate_diff(old, new)
    assert "password_hash" not in diff
    assert "identifier" not in diff
    assert "name" in diff
    assert diff["name"]["old"] == "John"
    assert diff["name"]["new"] == "Jane"

def test_generate_diff_serializes_complex_types():
    id_val = uuid.uuid4()
    old = {
        "amount": Decimal("100.50"), 
        "date": date(2023, 1, 1),
        "id": id_val
    }
    new = {
        "amount": Decimal("200.75"), 
        "date": date(2023, 1, 2),
        "id": id_val
    }
    
    diff = generate_diff(old, new)
    assert diff["amount"]["old"] == "100.50"
    assert diff["amount"]["new"] == "200.75"
    assert diff["date"]["old"] == "2023-01-01"
    assert diff["date"]["new"] == "2023-01-02"
    assert "id" not in diff # no change

@pytest.mark.asyncio
async def test_record_user_audit(app):
    from app.db.session import system_session
    from app.db.models import Company, User
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            db.add(Company(id=company_id, name="Test Company", base_currency="USD"))
            db.add(User(id=user_id, company_id=company_id, email="x@x.com", password_hash="h", name="t", role="owner"))
            
    user_ctx = UserCtx(user_id=str(user_id), company_id=str(company_id), role="owner")
    entity_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            await record_user_audit(
                session=db,
                user=user_ctx,
                entity_type="transaction",
                entity_id=entity_id,
                action="update",
                old_state={"amount": Decimal("100.00")},
                new_state={"amount": Decimal("200.00")},
                request_id=str(uuid.uuid4()),
                ip_address="127.0.0.1"
            )
        
    async with system_session() as db:
        result = await db.execute(select(AuditLog).where(AuditLog.entity_id == entity_id))
        log = result.scalars().first()
        
        assert log is not None
        assert log.actor_type == "user"
        assert log.actor_user_id == user_id
        assert log.diff["amount"]["new"] == "200.00"
        assert str(log.ip_address) == "127.0.0.1"

@pytest.mark.asyncio
async def test_record_system_audit(app):
    from app.db.session import system_session
    from app.db.models import Company
    company_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            db.add(Company(id=company_id, name="Test Company", base_currency="USD"))

    entity_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            await record_system_audit(
                session=db,
                company_id=company_id,
                task_name="check_alerts",
                entity_type="alert",
                entity_id=entity_id,
                action="create",
                old_state=None,
                new_state={"message": "ROI low"}
            )
        
    async with system_session() as db:
        result = await db.execute(select(AuditLog).where(AuditLog.entity_id == entity_id))
        log = result.scalars().first()
        
        assert log is not None
        assert log.actor_type == "system"
        assert log.actor_user_id is None
        assert log.source == "celery:check_alerts"
        assert log.diff["message"]["new"] == "ROI low"

