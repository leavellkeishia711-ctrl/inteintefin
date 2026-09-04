from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
import httpx
from datetime import datetime, timezone
import asyncio
import logging

from .base import Connector, NormalizedRecord, with_retry, ConnectorError, UnauthorizedError, RateLimitError
from app.db.session import async_session_maker, system_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.services.fx import resolve_fx_rate
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

class KeitaroConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str):
        super().__init__(config)
        self.api_key = decrypted_api_key
        self.base_url = "https://api.keitaro.io/v1" # Would be from config in reality

    async def _do_fetch(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        headers = {"Api-Key": self.api_key}
        response = await client.get(f"{self.base_url}/report", headers=headers, timeout=15)
        response.raise_for_status()
        
        try:
            data = response.json()
        except ValueError:
            raise ConnectorError("Malformed JSON in response")
            
        if not isinstance(data, list):
            raise ConnectorError("Unexpected response format, expected a list")
            
        return data

    async def fetch(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            return await with_retry(lambda: self._do_fetch(client))

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
        for row in raw_data:
            if not isinstance(row, dict):
                continue
                
            external_id = row.get("campaign_id")
            if external_id is None:
                continue
                
            date_str = row.get("date")
            if not date_str:
                continue
                
            try:
                stat_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
            except ValueError:
                continue
                
            try:
                spend = Decimal(str(row.get("spend", "0")))
                revenue = Decimal(str(row.get("revenue", "0")))
                if spend < 0 or revenue < 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                continue

            normalized.append(NormalizedRecord(
                source="keitaro",
                external_id=str(external_id),
                stat_date=stat_date,
                spend=spend,
                revenue=revenue,
                currency="USD"
            ))
            
        # Deduplicate taking the latest if multiple rows have same external_id and date
        unique_records = {}
        for rec in normalized:
            key = (rec.external_id, rec.stat_date)
            unique_records[key] = rec
            
        return list(unique_records.values())

    async def upsert(self, session: AsyncSession, normalized_data: List[NormalizedRecord]) -> None:
        # Get base currency for the company
        stmt_company = select(Company).where(Company.id == self.config.company_id)
        company_res = await session.execute(stmt_company)
        company = company_res.scalars().first()
        if not company:
            return
        base_currency = company.base_currency

        for record in normalized_data:
            # Find campaign run by note (which maps to Keitaro campaign_id)
            stmt = select(CampaignRun).where(
                and_(
                    CampaignRun.company_id == self.config.company_id,
                    CampaignRun.note == record.external_id
                )
            )
            run_res = await session.execute(stmt)
            run = run_res.scalars().first()
            if not run:
                continue # Skip unknown campaigns

            # Get fx rate
            try:
                fx_rate = await resolve_fx_rate(session, record.currency, base_currency, record.stat_date)
            except ValueError:
                fx_rate = Decimal("1.0") # Fallback or fail? We use 1.0 if not found, or maybe just skip
                
            # Upsert stat
            stmt_stat = select(CampaignRunStat).where(and_(
                CampaignRunStat.company_id == self.config.company_id,
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
                stat.fx_rate_to_base = fx_rate
            else:
                new_stat = CampaignRunStat(
                    company_id=self.config.company_id,
                    campaign_run_id=run.id,
                    stat_date=record.stat_date,
                    spend=record.spend,
                    revenue=record.revenue,
                    currency=record.currency,
                    fx_rate_to_base=fx_rate,
                    source=record.source,
                    external_id=record.external_id
                )
                session.add(new_stat)
                
        # Note: Do not commit here! The caller manages the transaction.

    async def test_connection(self) -> bool:
        return True

    async def fetch_campaigns(self) -> list:
        return []

    async def fetch_metrics(self) -> list:
        return []
