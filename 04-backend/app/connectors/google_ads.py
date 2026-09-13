import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal, InvalidOperation
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.connectors.base import Connector, NormalizedRecord, NormalizedAdAccount, with_retry, UnauthorizedError
from app.db.models.campaigns import CampaignRunStat, CampaignRun
from app.db.models.companies import Company
from app.services.fx import resolve_fx_rate

logger = logging.getLogger(__name__)

from app.core.config import settings
GOOGLE_ADS_API_VERSION = settings.GOOGLE_ADS_API_VERSION
GOOGLE_OAUTH2_TOKEN_URL = "https://oauth2.googleapis.com/token"

class GoogleAdsConnector(Connector):
    def __init__(self, config: Any, decrypted_api_key: str):
        super().__init__(config)
        try:
            creds = json.loads(decrypted_api_key)
            self.developer_token = creds["developer_token"]
            self.client_id = creds["client_id"]
            self.client_secret = creds["client_secret"]
            self.refresh_token = creds["refresh_token"]
            
            # Normalize IDs (remove hyphens, spaces)
            c_id = str(creds["customer_id"]).replace("-", "").replace(" ", "")
            self.customer_id = c_id
            
            l_id = creds.get("login_customer_id")
            if l_id:
                self.login_customer_id = str(l_id).replace("-", "").replace(" ", "")
            else:
                self.login_customer_id = None
                
        except (json.JSONDecodeError, KeyError, TypeError):
            raise ValueError("Invalid Google Ads credentials")

        self.access_token = None

    async def _refresh_access_token(self) -> None:
        """Fetch a new access token using the refresh token."""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token"
            }
            response = await with_retry(
                lambda: client.post(GOOGLE_OAUTH2_TOKEN_URL, data=data, timeout=15)
            )
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]

    def _get_headers(self) -> Dict[str, str]:
        if not self.access_token:
            raise ValueError("Access token is not set")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "developer-token": self.developer_token,
        }
        if self.login_customer_id:
            headers["login-customer-id"] = self.login_customer_id
        return headers

    async def _execute_gaql(self, query: str) -> List[Dict[str, Any]]:
        """Executes a GAQL query with pagination handling and automatic token refresh."""
        url = f"https://googleads.googleapis.com/{GOOGLE_ADS_API_VERSION}/customers/{self.customer_id}/googleAds:search"
        
        async def fetch_page(page_token: Optional[str] = None):
            if not self.access_token:
                await self._refresh_access_token()
                
            payload = {"query": query}
            if page_token:
                payload["pageToken"] = page_token
                
            async with httpx.AsyncClient() as client:
                try:
                    res = await with_retry(
                        lambda: client.post(
                            url,
                            headers=self._get_headers(),
                            json=payload,
                            timeout=30
                        )
                    )
                    res.raise_for_status()
                    return res.json()
                except UnauthorizedError:
                    # Refresh token and retry ONCE
                    await self._refresh_access_token()
                    res = await with_retry(
                        lambda: client.post(
                            url,
                            headers=self._get_headers(),
                            json=payload,
                            timeout=30
                        )
                    )
                    res.raise_for_status()
                    return res.json()

        all_results = []
        next_page_token = None
        
        while True:
            data = await fetch_page(next_page_token)
            results = data.get("results", [])
            all_results.extend(results)
            
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break
                
        return all_results

    async def test_connection(self) -> bool:
        query = "SELECT customer.id, customer.currency_code, customer.descriptive_name, customer.status FROM customer LIMIT 1"
        try:
            await self._execute_gaql(query)
            return True
        except UnauthorizedError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"Google Ads test_connection HTTP error: {type(e).__name__} status={e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Google Ads test_connection network error: {type(e).__name__}")
            return False

    async def fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        query = "SELECT customer.id, customer.currency_code, customer.descriptive_name, customer.status FROM customer LIMIT 1"
        return await self._execute_gaql(query)

    def normalize_ad_accounts(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedAdAccount]:
        normalized = []
        for row in raw_data:
            customer = row.get("customer", {})
            c_id = customer.get("id")
            if not c_id:
                continue
                
            raw_status = customer.get("status", "")
            if raw_status == "ENABLED":
                status = "active"
            elif raw_status == "SUSPENDED":
                status = "suspended"
            else:
                status = "banned"
                
            normalized.append(NormalizedAdAccount(
                platform="google_ads",
                external_account_id=str(c_id),
                status=status,
                name=customer.get("descriptiveName")
            ))
        return normalized

    async def fetch_campaigns(self) -> List[Dict[str, Any]]:
        query = "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, campaign.start_date, campaign.end_date FROM campaign WHERE campaign.status != 'REMOVED'"
        return await self._execute_gaql(query)

    async def fetch_metrics(self) -> List[Dict[str, Any]]:
        lookback_days = 7
        end_dt = datetime.now(timezone.utc).date()
        start_dt = end_dt - timedelta(days=lookback_days - 1)
        
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        
        query = f"SELECT campaign.id, campaign.name, segments.date, metrics.cost_micros, metrics.conversions_value, customer.id, customer.currency_code FROM campaign WHERE segments.date BETWEEN '{start_str}' AND '{end_str}' AND campaign.status != 'REMOVED'"
        return await self._execute_gaql(query)

    async def fetch(self) -> List[Dict[str, Any]]:
        return await self.fetch_metrics()

    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        normalized = []
        
        for row in raw_data:
            campaign = row.get("campaign", {})
            segments = row.get("segments", {})
            metrics = row.get("metrics", {})
            customer = row.get("customer", {})
            
            campaign_id = campaign.get("id")
            if not campaign_id:
                continue
                
            date_str = segments.get("date")
            if not date_str:
                continue
                
            currency_code = customer.get("currencyCode")
            if not currency_code or len(str(currency_code)) != 3:
                logger.warning(f"Google Ads missing or invalid currency code: {currency_code}")
                continue
                
            try:
                stat_date = date.fromisoformat(date_str)
            except ValueError:
                continue
                
            try:
                cost_micros = metrics.get("costMicros", "0")
                spend = Decimal(str(cost_micros)) / Decimal("1000000")
                
                conversions_value = metrics.get("conversionsValue", 0)
                revenue = Decimal(str(conversions_value or 0))
                
                if spend < 0 or revenue < 0:
                    continue
                    
            except (InvalidOperation, TypeError, ValueError):
                continue
                
            normalized.append(NormalizedRecord(
                source="google_ads",
                external_id=str(campaign_id),
                stat_date=stat_date,
                spend=spend,
                revenue=revenue,
                currency=str(currency_code)
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
                logger.error(f"Google Ads upsert FX rate error for external_id={record.external_id} date={record.stat_date}: {e}")
                raise
                
            await CampaignRunStat.upsert_campaign_run_stat_atomic(
                session=session,
                company_id=self.config.company_id,
                campaign_run_id=run.id,
                stat_date=record.stat_date,
                source=record.source,
                external_id=record.external_id,
                normalized_record=record,
                connector_name=self.__class__.__name__,
                fx_rate_to_base=fx_rate,
                currency=record.currency
            )
                
        if skipped > 0:
            logger.warning(f"Google Ads upsert skipped {skipped} records (unmatched CampaignRun.note), matched {matched}.")
