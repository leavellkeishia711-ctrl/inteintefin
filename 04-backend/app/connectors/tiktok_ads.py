import logging
import json
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from .base import Connector, NormalizedRecord, NormalizedAdAccount, with_retry, ConnectorError, UnauthorizedError, RateLimitError
from app.db.models.campaigns import ExternalCampaignMapping, CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.services.fx import resolve_fx_rate

logger = logging.getLogger(__name__)

class TikTokAdsConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str, timeout: int = 30):
        super().__init__(config, timeout=timeout)
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
        try:
            data = response.json()
        except Exception:
            data = {}

        api_code = str(data.get("code", "")) if "code" in data else None

        if response.status_code in {401, 403}:
            raise UnauthorizedError("TikTok Ads: Invalid or missing access token / permissions", status_code=response.status_code, api_error_code=api_code)
        if response.status_code == 429:
            raise RateLimitError("TikTok Ads: Rate limit exceeded", status_code=response.status_code, api_error_code=api_code)

        response.raise_for_status()

        if "code" in data and int(data.get("code", 0)) != 0:
            msg = data.get("message", "Unknown TikTok API Error")
            code_int = int(data.get("code", 0))
            if code_int in [40105, 40102, 40103, 40112]:
                raise UnauthorizedError(f"TikTok Ads API error: {msg}", status_code=response.status_code, api_error_code=api_code)
            elif code_int == 40104:
                raise RateLimitError(f"TikTok Ads API error: {msg}", status_code=response.status_code, api_error_code=api_code)
            raise ConnectorError(f"TikTok Ads API error: {msg}", status_code=response.status_code, api_error_code=api_code)

    async def test_connection(self) -> bool:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await with_retry(lambda: client.get(
                    f"{self.base_url}/advertiser/info/",
                    headers=self._get_headers(),
                    params={"advertiser_ids": json.dumps([self.advertiser_id])}
                ))
                self._raise_for_status(response)
                return True
            except Exception:
                return False

    async def fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
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

    async def fetch_metrics(self, start_date: Optional[date] = None, end_date: Optional[date] = None, page_size: Optional[int] = None, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
        # Fetch last 30 days like Meta Ads
        today = end_date or date.today()
        start_date = start_date or date.fromordinal(today.toordinal() - 30)
        end_date = end_date or today

        metrics = []
        page = 1
        pages_fetched = 0
        self.last_pages_fetched = 0
        self.last_saw_next_page = False

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while True:
                try:
                    response = await with_retry(lambda p=page: client.get(
                        f"{self.base_url}/report/integrated/get/",
                        headers=self._get_headers(),
                        params={
                            "advertiser_id": self.advertiser_id,
                            "report_type": "BASIC",
                            "data_level": "AUCTION_CAMPAIGN",
                            "dimensions": json.dumps(["campaign_id", "stat_time_day"]),
                            "metrics": json.dumps(["spend", "total_purchase_value", "clicks", "impressions", "conversion"]),
                            "start_date": start_date.strftime("%Y-%m-%d"),
                            "end_date": end_date.strftime("%Y-%m-%d"),
                            "page": p,
                            "page_size": page_size or 100
                        }
                    ))
                    self._raise_for_status(response)
                except Exception:
                    self.last_pages_fetched = pages_fetched
                    raise

                payload = response.json().get("data", {})
                metrics.extend(payload.get("list", []))

                pages_fetched += 1
                self.last_pages_fetched = pages_fetched

                page_info = payload.get("page_info", {})
                total_page = page_info.get("total_page", 1)

                self.last_saw_next_page = (page < total_page)

                if page >= total_page:
                    break

                if max_pages and pages_fetched >= max_pages:
                    break
                page += 1

        # To normalize, we also need currency. We can fetch it from advertiser_info.
        accounts = await self.fetch_ad_accounts()
        if not accounts or len(accounts) == 0:
            raise ConnectorError("No ad accounts returned, cannot determine currency")

        currency = accounts[0].get("currency")
        if not currency:
            raise ConnectorError("Advertiser account is missing currency")

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

                currency = row.get("_currency")
                if not currency:
                    raise ConnectorError("Missing currency in TikTok Ads metrics")

                clicks_str = str(metrics.get("clicks") or "0").replace(",", "")
                impressions_str = str(metrics.get("impressions") or "0").replace(",", "")
                conversions_str = str(metrics.get("conversion") or "0").replace(",", "")

                try:
                    clicks = int(clicks_str)
                    if clicks < 0: clicks = 0
                except ValueError:
                    clicks = 0

                try:
                    impressions = int(impressions_str)
                    if impressions < 0: impressions = 0
                except ValueError:
                    impressions = 0

                try:
                    conversions = Decimal(conversions_str)
                    if conversions < 0: conversions = Decimal("0")
                except (InvalidOperation, TypeError, ValueError):
                    conversions = Decimal("0")

                normalized.append(
                    NormalizedRecord(
                        source="tiktok_ads",
                        external_id=campaign_id,
                        stat_date=stat_date,
                        spend=spend,
                        revenue=revenue,
                        currency=currency,
                        clicks=clicks,
                        impressions=impressions,
                        conversions=conversions
                    )
                )
            except ConnectorError:
                raise
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.warning(f"Failed to normalize TikTok row: {e}")
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
            stmt = select(CampaignRun).join(ExternalCampaignMapping, CampaignRun.id == ExternalCampaignMapping.campaign_run_id).where(
                and_(
                    ExternalCampaignMapping.company_id == company_id,
                    ExternalCampaignMapping.platform == self.config.connector_name,
                    ExternalCampaignMapping.external_id == record.external_id,
                    ExternalCampaignMapping.deleted_at.is_(None),
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
                normalized_record=record,
                connector_name=self.__class__.__name__,
                fx_rate_to_base=fx_rate,
                currency=record.currency
            )

