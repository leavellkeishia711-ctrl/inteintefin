import logging
import json
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .base import Connector, NormalizedRecord, NormalizedAdAccount, with_retry, ConnectorError, UnauthorizedError, RateLimitError
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.services.fx import resolve_fx_rate

logger = logging.getLogger(__name__)

class TikTokAdsConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str):
        super().__init__(config)
        # decrypted_api_key must be a JSON string containing access_token and advertiser_id
        try:
            creds = json.loads(decrypted_api_key)
            self.access_token = creds.get("access_token")
            self.advertiser_id = str(creds.get("advertiser_id", ""))
            
            if not self.access_token or not self.advertiser_id:
                raise ValueError("TikTok Ads credentials must contain 'access_token' and 'advertiser_id'")
        except json.JSONDecodeError:
            raise ValueError("TikTok Ads credentials must be a valid JSON string")
            
        self.base_url = "https://business-api.tiktok.com/open_api/v1.3"
        
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code in {401, 403}:
            raise UnauthorizedError("TikTok Ads: Invalid or missing access token / permissions")
        if response.status_code == 429:
            raise RateLimitError("TikTok Ads: Rate limit exceeded")
        
        try:
            response.raise_for_status()
            data = response.json()
            if int(data.get("code", 0)) != 0:
                msg = data.get("message", "Unknown TikTok API Error")
                
                # Check TikTok-specific auth/permission codes
                if data.get("code") in {40105, 40102, 40103, 40112}:
                    raise UnauthorizedError(f"TikTok Ads: {msg}")
                # Check TikTok-specific rate limit codes
                if data.get("code") == 40104:
                    raise RateLimitError(f"TikTok Ads: {msg}")
                    
                raise ConnectorError(f"TikTok Ads API error: {msg}")
        except httpx.HTTPStatusError as e:
            raise ConnectorError(f"TikTok Ads HTTP error: {e}")
        except ValueError as e:
             raise ConnectorError(f"TikTok Ads invalid response: {e}")

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                # Use advertiser/info to verify token and advertiser_id
                response = await with_retry(lambda: client.get(
                    f"{self.base_url}/advertiser/info/",
                    headers=self._get_headers(),
                    params={"advertiser_ids": json.dumps([self.advertiser_id])}
                ))
                self._raise_for_status(response)
                return True
            except (UnauthorizedError, ValueError):
                return False

    async def fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await with_retry(lambda: client.get(
                f"{self.base_url}/advertiser/info/",
                headers=self._get_headers(),
                params={"advertiser_ids": json.dumps([self.advertiser_id])}
            ))
            self._raise_for_status(response)
            data = response.json().get("data", {}).get("list", [])
            return data

    def normalize_ad_accounts(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedAdAccount]:
        accounts = []
        for account in raw_data:
            accounts.append(
                NormalizedAdAccount(
                    platform="tiktok_ads",
                    external_account_id=str(account.get("advertiser_id")),
                    name=account.get("name", "Unknown TikTok Account"),
                    status="active" # TikTok doesn't provide a direct active status in info list
                )
            )
        return accounts

    async def fetch_campaigns(self) -> List[Dict[str, Any]]:
        campaigns = []
        page = 1
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                response = await with_retry(lambda p=page: client.get(
                    f"{self.base_url}/campaign/get/",
                    headers=self._get_headers(),
                    params={
                        "advertiser_id": self.advertiser_id,
                        "page": p,
                        "page_size": 100
                    }
                ))
                self._raise_for_status(response)
                payload = response.json().get("data", {})
                campaigns.extend(payload.get("list", []))
                
                page_info = payload.get("page_info", {})
                total_page = page_info.get("total_page", 1)
                
                if page >= total_page:
                    break
                page += 1
        return campaigns

    async def fetch(self) -> List[Dict[str, Any]]:
        return await self.fetch_metrics()

    async def fetch_metrics(self) -> List[Dict[str, Any]]:
        # Fetch last 30 days like Meta Ads
        today = date.today()
        start_date = date.fromordinal(today.toordinal() - 30)
        
        metrics = []
        page = 1
        async with httpx.AsyncClient(timeout=30) as client:
            while True:
                response = await with_retry(lambda p=page: client.get(
                    f"{self.base_url}/report/integrated/get/",
                    headers=self._get_headers(),
                    params={
                        "advertiser_id": self.advertiser_id,
                        "report_type": "BASIC",
                        "data_level": "AUCTION_CAMPAIGN",
                        "dimensions": json.dumps(["campaign_id", "stat_time_day"]),
                        "metrics": json.dumps(["spend", "total_purchase_value"]),
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": today.strftime("%Y-%m-%d"),
                        "page": p,
                        "page_size": 100
                    }
                ))
                self._raise_for_status(response)
                payload = response.json().get("data", {})
                metrics.extend(payload.get("list", []))
                
                page_info = payload.get("page_info", {})
                total_page = page_info.get("total_page", 1)
                
                if page >= total_page:
                    break
                page += 1
                
        # To normalize, we also need currency. We can fetch it from advertiser_info.
        accounts = await self.fetch_ad_accounts()
        currency = "USD"
        if accounts and len(accounts) > 0:
            currency = accounts[0].get("currency", "USD")
            
        # Attach currency to metrics so `normalize` has access to it.
        for m in metrics:
            m["_currency"] = currency
            
        return metrics

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
        for row in raw_data:
            try:
                metrics = row.get("metrics", {})
                dimensions = row.get("dimensions", {})
                
                campaign_id = str(dimensions.get("campaign_id", ""))
                date_str = dimensions.get("stat_time_day")
                
                if not campaign_id or not date_str:
                    continue
                    
                stat_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                spend_str = str(metrics.get("spend") or "0").replace(",", "")
                rev_str = str(metrics.get("total_purchase_value") or "0").replace(",", "")
                
                spend = Decimal(spend_str)
                revenue = Decimal(rev_str)
                currency = row.get("_currency", "USD")
                
                normalized.append(
                    NormalizedRecord(
                        source="tiktok_ads",
                        external_id=campaign_id,
                        stat_date=stat_date,
                        spend=spend,
                        revenue=revenue,
                        currency=currency
                    )
                )
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Failed to normalize TikTok row: {e}, row={row}")
                continue
                
        # Dedupe by (external_id, stat_date) preferring last seen (simplistic approach, similar to others)
        deduped = {}
        for r in normalized:
            deduped[(r.external_id, r.stat_date)] = r
        return list(deduped.values())

    async def upsert(self, session: AsyncSession, normalized_data: List[NormalizedRecord]) -> None:
        if not normalized_data:
            return

        company_id = self.config.company_id
        company = await session.scalar(select(Company).where(Company.id == company_id))
        if not company:
            logger.error(f"Company {company_id} not found")
            return
            
        base_currency = company.base_currency or "USD"
        
        for record in normalized_data:
            stmt = select(CampaignRun).where(
                and_(
                    CampaignRun.company_id == company_id,
                    CampaignRun.note == record.external_id,
                    CampaignRun.deleted_at.is_(None)
                )
            )
            run = await session.scalar(stmt)
            if not run:
                logger.debug(f"TikTok Ads: No CampaignRun found for external_id={record.external_id}")
                continue
                
            fx_rate = await resolve_fx_rate(
                session=session,
                from_currency=record.currency,
                to_currency=base_currency,
                date_val=record.stat_date
            )
            
            await CampaignRunStat.upsert_campaign_run_stat_atomic(
                session=session,
                company_id=company_id,
                campaign_run_id=run.id,
                stat_date=record.stat_date,
                source=record.source,
                external_id=record.external_id,
                normalized_record=record,
                connector_name=self.__class__.__name__,
                fx_rate_to_base=fx_rate,
                currency=record.currency
            )
