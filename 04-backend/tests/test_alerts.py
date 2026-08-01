import pytest
from app.services.alerts import check_financial_alerts
from app.db.models import Company
from decimal import Decimal
import uuid
from app.db.session import system_session

@pytest.mark.asyncio
async def test_check_financial_alerts_roi():
    async with system_session() as db_session:
        async with db_session.begin():
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
            # Let's verify it runs without errors for a fresh company
            await check_financial_alerts(db_session_query, company.id)
