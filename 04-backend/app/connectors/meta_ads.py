from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
import httpx
from datetime import datetime, timezone
import logging
from .base import Connector, NormalizedRecord, NormalizedAdAccount, with_retry
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.services.fx import resolve_fx_rate
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

class MetaAdsConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str):
        super().__init__(config)
        self.api_key = decrypted_api_key
        settings = getattr(config, 'settings', {}) or {}
        self.base_url = settings.get("base_url", "https://graph.facebook.com/v19.0").rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        """Meta Graph API strictly uses Bearer token in Authorization header."""
        return {"Authorization": f"Bearer {self.api_key}"}

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                headers = self._get_headers()
                response = await with_retry(lambda: client.get(
                    f"{self.base_url}/me?fields=id,name",
                    headers=headers,
                    timeout=10
                ))
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as e:
                logger.error(f"MetaAds test_connection HTTP error: {type(e).__name__} status={e.response.status_code}")
                return False
            except Exception as e:
                logger.error(f"MetaAds test_connection network error: {type(e).__name__}")
                return False

    async def fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            response = await with_retry(lambda: client.get(
                f"{self.base_url}/me/adaccounts?fields=account_id,name,account_status",
                headers=headers,
                timeout=15
            ))
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []

    def normalize_ad_accounts(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedAdAccount]:
        normalized = []
        for row in raw_data:
            if not isinstance(row, dict):
                continue
                
            acc_id = row.get("account_id")
            if not acc_id:
                continue
                
            # Meta status: 1 = ACTIVE, 2 = DISABLED, 3 = UNSETTLED, 7 = PENDING_RISK_REVIEW, 8 = PENDING_SETTLEMENT, 9 = IN_GRACE_PERIOD, 100 = PENDING_CLOSURE, 101 = CLOSED, 201 = ANY_ACTIVE, 202 = ANY_CLOSED
            raw_status = row.get("account_status", 0)
            status_map = {1: "active"}
            mapped_status = status_map.get(raw_status, "disabled")
            
            normalized.append(NormalizedAdAccount(
                platform="meta",
                external_account_id=str(acc_id),
                status=mapped_status,
                name=row.get("name")
            ))
        return normalized

    async def fetch_campaigns(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            response = await with_retry(lambda: client.get(
                f"{self.base_url}/me/adaccounts?fields=campaigns{{id,name}}",
                headers=headers,
                timeout=15
            ))
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            return data if isinstance(data, list) else []

    async def fetch_metrics(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            response = await with_retry(lambda: client.get(
                f"{self.base_url}/me/adaccounts?fields=insights.level(campaign){{campaign_id,spend,date_start}}",
                headers=headers,
                timeout=15
            ))
            response.raise_for_status()
            data = response.json()
            
            metrics = []
            if isinstance(data, dict) and "data" in data:
                for account in data["data"]:
                    insights = account.get("insights", {}).get("data", [])
                    metrics.extend(insights)
                return metrics
            
            return data if isinstance(data, list) else []

    async def fetch(self) -> List[Dict[str, Any]]:
        return await self.fetch_metrics()

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
        settings = getattr(self.config, 'settings', {}) or {}
        currency = str(settings.get("currency", "USD"))
        if len(currency) != 3:
            currency = "USD"
            
        for row in raw_data:
            if not isinstance(row, dict):
                continue
                
            external_id = row.get("campaign_id")
            if external_id is None:
                continue
                
            date_str = row.get("date_start")
            if not date_str:
                stat_date = datetime.now(timezone.utc).date()
            else:
                try:
                    stat_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
                except ValueError:
                    continue
                
            try:
                spend = Decimal(str(row.get("spend", "0")))
                # Revenue in Meta is complex (action_values etc). We assume 0 or it's mapped by an aggregator
                revenue = Decimal(str(row.get("revenue", "0"))) 
                if spend < 0 or revenue < 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                continue

            normalized.append(NormalizedRecord(
                source="meta",
                external_id=str(external_id),
                stat_date=stat_date,
                spend=spend,
                revenue=revenue,
                currency=currency
            ))
            
        unique_records = {}
        for rec in normalized:
            key = (rec.external_id, rec.stat_date)
            unique_records[key] = rec
            
        return list(unique_records.values())

    async def upsert(self, session: AsyncSession, normalized_data: List[NormalizedRecord]) -> None:
        stmt_company = select(Company).where(Company.id == self.config.company_id)
        company_res = await session.execute(stmt_company)
        company = company_res.scalars().first()
        if not company:
            return
        base_currency = company.base_currency

        matched = 0
        skipped = 0

        for record in normalized_data:
            stmt = select(CampaignRun).where(
                and_(
                    CampaignRun.company_id == self.config.company_id,
                    CampaignRun.note == record.external_id,
                    CampaignRun.deleted_at.is_(None)
                )
            )
            run_res = await session.execute(stmt)
            run = run_res.scalars().first()
            if not run:
                skipped += 1
                continue
                
            matched += 1

            try:
                fx_rate = await resolve_fx_rate(session, record.currency, base_currency, record.stat_date)
            except ValueError:
                fx_rate = Decimal("1.0")
                
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
                
        if skipped > 0:
            logger.warning(f"MetaAds upsert skipped {skipped} records (unmatched CampaignRun.note), matched {matched}.")
