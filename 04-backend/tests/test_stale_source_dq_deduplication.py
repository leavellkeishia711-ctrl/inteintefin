import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.db.session import system_session
from sqlalchemy import select
from app.db.models.connectors import ConnectorConfig
from app.services.data_quality import monitor_stalled_data
from app.db.models.system import Alert

pytestmark = pytest.mark.asyncio

async def test_stale_source_dq_dedup(company_b_fixtures):
    comp_id = uuid.UUID(company_b_fixtures.ids["company_id"])
    
    now = datetime.now(timezone.utc)
    
    async with system_session() as db_session:
        conn = ConnectorConfig(
            company_id=comp_id,
            connector_name="keitaro",
            status="active",
            encrypted_secret="enc",
            sync_interval_minutes=60,
            last_successful_sync=now - timedelta(hours=4)
        )
        db_session.add(conn)
        await db_session.commit()
        
        # Run once
        await monitor_stalled_data(db_session, comp_id)
        await db_session.commit()
        
        # Run twice
        await monitor_stalled_data(db_session, comp_id)
        await db_session.commit()
        
        res = await db_session.execute(select(Alert).where(Alert.company_id == comp_id))
        alerts = res.scalars().all()
        stale_alerts = [a for a in alerts if "Data Quality Alert" in a.message]
        assert len(stale_alerts) == 1 # Deduplicated by trigger_alert logic (which uses dedup_key)
