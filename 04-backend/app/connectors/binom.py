from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
import httpx
from datetime import datetime, timezone
import logging
from .base import Connector, NormalizedRecord, with_retry
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.campaigns import ExternalCampaignMapping, CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.services.fx import resolve_fx_rate
from sqlalchemy import select, and_
import urllib.parse

logger = logging.getLogger(__name__)

class BinomConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str):
        super().__init__(config)
        self.api_key = decrypted_api_key
        settings = getattr(config, 'settings', {}) or {}
        
        base_url = settings.get("base_url", "").strip()
        if not base_url:
            raise ValueError("Binom base_url must be provided")
            
        # Normalize base_url
        if base_url.endswith("/index") or base_url.endswith("/index.php"):
            logger.warning(f"Normalizing Binom base_url from {base_url}")
            base_url = base_url.replace("/index.php", "").replace("/index", "")
            
        self.base_url = base_url.rstrip("/")
        
        self.currency = settings.get("currency")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("BINOM_CURRENCY is missing or invalid in configuration")

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient() as client:
            try:
                headers = {"Api-Key": self.api_key}
                response = await with_retry(lambda: client.get(
                    f"{self.base_url}/api/v2/campaigns",
                    headers=headers,
                    timeout=10
                ))
                response.raise_for_status()
                return True
            except httpx.HTTPStatusError as e:
                logger.error(f"Binom test_connection HTTP error: {type(e).__name__} status={e.response.status_code}")
                return False
            except Exception as e:
                logger.error(f"Binom test_connection network error: {type(e).__name__}")
                return False

    async def fetch_campaigns(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            headers = {"Api-Key": self.api_key}
            response = await with_retry(lambda: client.get(
                f"{self.base_url}/api/v2/campaigns",
                headers=headers,
                timeout=15
            ))
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []

    async def fetch_metrics(self, start_date=None, end_date=None) -> List[Dict[str, Any]]:
        if start_date or end_date:
            raise NotImplementedError(f"{self.__class__.__name__} does not support date range in fetch_metrics yet")
            
        async with httpx.AsyncClient() as client:
            headers = {"Api-Key": self.api_key}
            response = await with_retry(lambda: client.get(
                f"{self.base_url}/api/v2/stats",
                headers=headers,
                timeout=15
            ))
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []

    async def fetch(self) -> List[Dict[str, Any]]:
        return await self.fetch_metrics()

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []

        for row in raw_data:
            if not isinstance(row, dict):
                continue

            external_id = row.get("camp_id") or row.get("id")
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
                spend = Decimal(str(row.get("cost", "0")))
                revenue = Decimal(str(row.get("revenue", "0")))
                if spend < 0 or revenue < 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                continue

            try:
                clicks = int(str(row.get("clicks", "0") or "0"))
                if clicks < 0: clicks = 0
            except ValueError:
                clicks = 0

            try:
                impressions = int(str(row.get("impressions", "0") or "0"))
                if impressions < 0: impressions = 0
            except ValueError:
                impressions = 0

            try:
                raw_conv = row.get("conversions") if "conversions" in row else row.get("leads")
                conversions = Decimal(str(raw_conv or "0"))
                if conversions < 0: conversions = Decimal("0")
            except (InvalidOperation, TypeError, ValueError):
                conversions = Decimal("0")

            normalized.append(NormalizedRecord(
                source="binom",
                external_id=str(external_id),
                stat_date=stat_date,
                spend=spend,
                revenue=revenue,
                currency=self.currency,
                clicks=clicks,
                impressions=impressions,
                conversions=conversions
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
            stmt = select(CampaignRun).join(ExternalCampaignMapping, CampaignRun.id == ExternalCampaignMapping.campaign_run_id).where(
                and_(
                    ExternalCampaignMapping.company_id == self.config.company_id,
                    ExternalCampaignMapping.platform == self.config.connector_name,
                    ExternalCampaignMapping.external_id == record.external_id,
                    ExternalCampaignMapping.deleted_at.is_(None),
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
            except ValueError as e:
                logger.error(f"Binom upsert FX rate error for external_id={record.external_id} date={record.stat_date}: {e}")
                raise

            await CampaignRunStat.upsert_campaign_run_stat_atomic(
                session=session,
                company_id=self.config.company_id,
                campaign_run_id=run.id,
                stat_date=record.stat_date,
                source=record.source,
                normalized_record=record,
                connector_name=self.__class__.__name__,
                fx_rate_to_base=fx_rate,
                currency=record.currency
            )

        if skipped > 0:
            logger.warning(f"Binom upsert skipped {skipped} records (unmatched CampaignRun.note), matched {matched}.")
