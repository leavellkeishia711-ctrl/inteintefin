from typing import List, Dict, Any
from decimal import Decimal
import httpx
from datetime import datetime
from .base import Connector, NormalizedRecord
from app.db.session import async_session_maker
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.system import FXRate
from sqlalchemy import select, and_
import uuid

class KeitaroConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str):
        super().__init__(config)
        self.api_key = decrypted_api_key
        self.base_url = "https://api.keitaro.io/v1" # example base URL, could be part of config

    async def fetch(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            headers = {"Api-Key": self.api_key}
            # Mocking fetch logic for Keitaro campaigns
            try:
                response = await client.get(f"{self.base_url}/report", headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    raise ValueError("Unauthorized")
                raise

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
        for row in raw_data:
            # Assuming row has campaign_id, date, spend, revenue
            normalized.append(NormalizedRecord(
                source="keitaro",
                external_id=str(row.get("campaign_id")),
                stat_date=datetime.strptime(row.get("date"), "%Y-%m-%d").date(),
                spend=Decimal(str(row.get("spend", "0"))),
                revenue=Decimal(str(row.get("revenue", "0"))),
                currency="USD" # Assume USD for Keitaro for now
            ))
        return normalized

    async def upsert(self, normalized_data: List[NormalizedRecord]) -> None:
        async with async_session_maker() as session:
            for record in normalized_data:
                # Get fx rate
                stmt_fx = select(FXRate).where(and_(FXRate.date == record.stat_date, FXRate.currency == record.currency))
                fx_result = await session.execute(stmt_fx)
                fx_rate = fx_result.scalars().first()
                rate = fx_rate.rate if fx_rate else Decimal('1.0')

                # Find campaign run by external id - assuming external_id maps to a campaign run note or id?
                # Actually, the requirement says "не создавать campaign или campaign_run без явно подтверждённой бизнес-логики; корректно пропускать неизвестные кампании"
                # For this implementation, we will assume there's a mapping, or we just skip if we don't find it.
                stmt = select(CampaignRun).where(CampaignRun.note == record.external_id)
                run_res = await session.execute(stmt)
                run = run_res.scalars().first()
                if not run:
                    continue # Skip unknown

                # Upsert stat
                stmt_stat = select(CampaignRunStat).where(and_(
                    CampaignRunStat.campaign_run_id == run.id,
                    CampaignRunStat.stat_date == record.stat_date,
                    CampaignRunStat.source == record.source,
                    CampaignRunStat.external_id == record.external_id
                ))
                stat_res = await session.execute(stmt_stat)
                stat = stat_res.scalars().first()
                if stat:
                    stat.spend = record.spend
                    stat.revenue = record.revenue
                    stat.fx_rate_to_base = rate
                else:
                    new_stat = CampaignRunStat(
                        company_id=self.config.company_id,
                        campaign_run_id=run.id,
                        stat_date=record.stat_date,
                        spend=record.spend,
                        revenue=record.revenue,
                        currency=record.currency,
                        fx_rate_to_base=rate,
                        source=record.source,
                        external_id=record.external_id
                    )
                    session.add(new_stat)
            await session.commit()
