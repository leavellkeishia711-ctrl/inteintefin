import asyncio
import logging
from sqlalchemy import select
from celery.schedules import crontab
from app.workers.celery_app import celery_app
from app.db.models import Company
from app.db.session import system_session, tenant_session
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def tenant_task_session(company_id: str):
    """
    Context manager for background tasks to ensure they only access data
    for a specific company with proper RLS enforced.
    """
    async with tenant_session(company_id) as db:
        yield db

async def execute_for_all_tenants(task_func):
    """
    Executes a given async function for all active companies.
    Ensures that each company is handled in its own isolated RLS context.
    """
    try:
        async with system_session() as db:
            result = await db.execute(select(Company.id))
            company_ids = result.scalars().all()
            
        for cid in company_ids:
            try:
                async with tenant_task_session(str(cid)) as tenant_db:
                    await task_func(tenant_db, cid)
            except Exception as e:
                logger.error(f"Error executing task for company {cid}: {e}")
    except Exception as e:
        logger.error(f"Error fetching companies for task: {e}")

@celery_app.task(name="check_alerts")
def check_alerts_task():
    async def _check_alerts_impl():
        async def _run_for_company(db, company_id):
            from app.services.alerts import check_financial_alerts
            logger.info(f"Running check_alerts for company {company_id}")
            await check_financial_alerts(db, company_id)
            
        await execute_for_all_tenants(_run_for_company)
        
    asyncio.run(_check_alerts_impl())

@celery_app.task(name="monitor_data_quality")
def monitor_data_quality_task():
    async def _monitor_impl():
        async def _run_for_company(db, company_id):
            from app.services.data_quality import monitor_stalled_data
            logger.info(f"Running monitor_data_quality for company {company_id}")
            await monitor_stalled_data(db, company_id)
            
        await execute_for_all_tenants(_run_for_company)

    asyncio.run(_monitor_impl())

# Setup Celery Beat
celery_app.conf.beat_schedule = {
    "check-alerts-every-hour": {
        "task": "check_alerts",
        "schedule": 3600.0,
    },
    "monitor-data-quality-every-day": {
        "task": "monitor_data_quality",
        "schedule": crontab(hour=0, minute=0), # Daily at midnight UTC
    },
}

@celery_app.task(name='sync_connectors_task')
def sync_connectors_task():
    from app.connectors.scheduler import run_scheduled_syncs
    asyncio.run(run_scheduled_syncs())

celery_app.conf.beat_schedule['sync-connectors-every-hour'] = {
    'task': 'sync_connectors_task',
    'schedule': 3600.0,
}
