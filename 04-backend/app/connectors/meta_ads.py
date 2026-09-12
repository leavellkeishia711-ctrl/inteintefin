from typing import List, Dict, Any
from decimal import Decimal, InvalidOperation
import httpx
from datetime import datetime, timezone
import logging
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
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
        
    def _sanitize_url(self, url: str) -> str:
        """Removes credential query parameters from paging URLs."""
        if not url:
            return url
        parsed = urlparse(url)
        qsl = parse_qsl(parsed.query, keep_blank_values=True)
        clean_qsl = [(k, v) for k, v in qsl if k.lower() not in ("access_token", "token", "appsecret_proof")]
        new_query = urlencode(clean_qsl)
        return urlunparse(parsed._replace(query=new_query))

    async def _fetch_all_pages(self, url: str) -> List[Dict[str, Any]]:
        """Helper to fetch all pages following Meta Graph API paging.next."""
        results = []
        current_url = url
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            while current_url:
                clean_url = self._sanitize_url(current_url)
                response = await with_retry(lambda u=clean_url: client.get(
                    u,
                    headers=headers,
                    timeout=15
                ))
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, dict) and "data" in data:
                    results.extend(data["data"])
                elif isinstance(data, list):
                    results.extend(data)
                
                # Check for next page
                paging = data.get("paging", {}) if isinstance(data, dict) else {}
                next_url = paging.get("next")
                
                # Safety check to prevent infinite loops if API is misbehaving
                if next_url and next_url == current_url:
                    break
                current_url = next_url
        return results

    async def test_connection(self) -> bool:
        from .base import UnauthorizedError
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
            except UnauthorizedError:
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"MetaAds test_connection HTTP error: {type(e).__name__} status={e.response.status_code}")
                return False
            except Exception as e:
                logger.error(f"MetaAds test_connection network error: {type(e).__name__}")
                return False

    async def fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/me/adaccounts?fields=account_id,name,account_status"
        return await self._fetch_all_pages(url)

    def normalize_ad_accounts(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedAdAccount]:
        normalized = []
        for row in raw_data:
            if not isinstance(row, dict):
                continue
                
            acc_id = row.get("account_id")
            if not acc_id:
                continue
                
            raw_status = row.get("account_status", 0)
            status_map = {1: "active", 3: "suspended", 7: "suspended", 8: "suspended", 9: "suspended", 2: "banned", 100: "banned", 101: "banned"}
            mapped_status = status_map.get(raw_status, "banned")
            
            normalized.append(NormalizedAdAccount(
                platform="meta",
                external_account_id=str(acc_id),
                status=mapped_status,
                name=row.get("name")
            ))
        return normalized

    async def fetch_campaigns(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/me/adaccounts?fields=campaigns{{id,name}}"
        accounts = await self._fetch_all_pages(url)
        
        flat_campaigns = []
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            for account in accounts:
                if not isinstance(account, dict):
                    continue
                acc_id = account.get("id")
                campaigns = account.get("campaigns", {})
                campaigns_data = campaigns.get("data", [])
                for camp in campaigns_data:
                    if isinstance(camp, dict):
                        camp_copy = dict(camp)
                        camp_copy["account_id"] = acc_id
                        flat_campaigns.append(camp_copy)
                        
                paging = campaigns.get("paging", {})
                next_url = paging.get("next")
                
                while next_url:
                    clean_next = self._sanitize_url(next_url)
                    response = await with_retry(lambda u=clean_next: client.get(
                        u,
                        headers=headers,
                        timeout=15
                    ))
                    response.raise_for_status()
                    data = response.json()
                    
                    if isinstance(data, dict) and "data" in data:
                        for camp in data["data"]:
                            if isinstance(camp, dict):
                                camp_copy = dict(camp)
                                camp_copy["account_id"] = acc_id
                                flat_campaigns.append(camp_copy)
                    
                    new_paging = data.get("paging", {}) if isinstance(data, dict) else {}
                    new_next_url = new_paging.get("next")
                    
                    if new_next_url:
                        clean_new_next = self._sanitize_url(new_next_url)
                        if clean_new_next == clean_next:
                            break
                            
                    next_url = new_next_url
                    
        return flat_campaigns

    async def fetch_metrics(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/me/adaccounts?fields=insights.level(campaign){{campaign_id,spend,action_values,clicks,impressions,reach,actions,date_start}}"
        accounts = await self._fetch_all_pages(url)
        
        metrics = []
        async with httpx.AsyncClient() as client:
            headers = self._get_headers()
            for account in accounts:
                if not isinstance(account, dict):
                    continue
                insights = account.get("insights", {})
                insights_data = insights.get("data", [])
                metrics.extend(insights_data)
                
                paging = insights.get("paging", {})
                next_url = paging.get("next")
                
                while next_url:
                    clean_next = self._sanitize_url(next_url)
                    response = await with_retry(lambda u=clean_next: client.get(
                        u,
                        headers=headers,
                        timeout=15
                    ))
                    response.raise_for_status()
                    data = response.json()
                    
                    if isinstance(data, dict) and "data" in data:
                        metrics.extend(data["data"])
                    
                    new_paging = data.get("paging", {}) if isinstance(data, dict) else {}
                    new_next_url = new_paging.get("next")
                    
                    if new_next_url:
                        clean_new_next = self._sanitize_url(new_next_url)
                        if clean_new_next == clean_next:
                            break
                            
                    next_url = new_next_url
                    
        return metrics

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
                continue
            try:
                stat_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
            except ValueError:
                continue
                
            try:
                spend = Decimal(str(row.get("spend", "0")))
                if spend < 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError, ValueError):
                continue
                
            revenue = Decimal("0")
            action_values = row.get("action_values")
            if isinstance(action_values, list):
                for action in action_values:
                    if isinstance(action, dict) and action.get("action_type") in ("purchase", "omni_purchase"):
                        try:
                            val = Decimal(str(action.get("value", "0")))
                            if val > 0:
                                revenue += val
                        except (InvalidOperation, TypeError, ValueError):
                            pass

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
            except ValueError as e:
                logger.error(f"MetaAds upsert FX rate error for source={record.source} external_id={record.external_id} date={record.stat_date}: {e}")
                raise
                
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
