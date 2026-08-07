import pytest
from app.services.alerts import check_financial_alerts, trigger_alert
from app.db.models import Company, Alert
from decimal import Decimal
import uuid
from app.db.session import system_session
from sqlalchemy import select

@pytest.mark.asyncio
async def test_alert_deduplication():
    async with system_session() as db_session:
        company_id = uuid.uuid4()
        async with db_session.begin():
            company = Company(
                id=company_id,
                name="Dedup Test Company",
                base_currency="USD",
                alert_roi_threshold=Decimal("-10.0000"),
                alert_runway_threshold_days=30
            )
            db_session.add(company)
            
        async with db_session.begin():
            # Trigger first alert
            await trigger_alert(
                db_session, company_id,
                type="financial",
                risk_level="warning",
                message="Test",
                dedup_key="test_dedup",
                cooldown_hours=24
            )
            
            # Trigger second alert (should be skipped)
            await trigger_alert(
                db_session, company_id,
                type="financial",
                risk_level="warning",
                message="Test 2",
                dedup_key="test_dedup",
                cooldown_hours=24
            )
            
            result = await db_session.execute(select(Alert).where(Alert.company_id == company_id))
            alerts = result.scalars().all()
            assert len(alerts) == 1
            assert alerts[0].message == "Test"

@pytest.mark.asyncio
async def test_check_financial_alerts_roi():
    async with system_session() as db_session:
        company = Company(
            id=uuid.uuid4(),
            name="Alerts Test Company",
            base_currency="USD",
            alert_roi_threshold=Decimal("-10.0000"),
            alert_runway_threshold_days=30
        )
        db_session.add(company)
        await db_session.commit()
            
        async with system_session() as db_session_query:
            await check_financial_alerts(db_session_query, company.id)
