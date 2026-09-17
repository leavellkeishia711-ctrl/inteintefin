from abc import ABC, abstractmethod
from typing import Dict, Any, List, TypeVar, Callable, Awaitable, Optional
from pydantic import BaseModel, Field
import uuid
import httpx
import asyncio
import logging
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

class ConnectorError(Exception):
    """Base exception for connector errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, api_error_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.api_error_code = api_error_code

class UnauthorizedError(ConnectorError):
    """Raised when the connector receives an HTTP 401 or 403."""
    pass

class RateLimitError(ConnectorError):
    """Raised when the connector is rate-limited (HTTP 429) and max retries are exceeded."""
    pass

T = TypeVar('T')

async def with_retry(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    base_delay: int = 1,
    retry_statuses: tuple = (429, 500, 502, 503, 504)
) -> T:
    """
    Executes an async function with exponential backoff.
    Raises UnauthorizedError for 401/403.
    Retries for specified statuses (default: 429, 50x) and connection timeouts.
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except httpx.HTTPStatusError as e:
            api_err = None
            try:
                body = e.response.json()
                if "error" in body and isinstance(body["error"], dict):
                    # Google format: body.error.details[0].errors[0].errorCode...
                    details = body["error"].get("details", [])
                    if details and "errors" in details[0]:
                        errs = details[0]["errors"]
                        if errs and "errorCode" in errs[0]:
                            err_code_dict = errs[0]["errorCode"]
                            if isinstance(err_code_dict, dict):
                                api_err = list(err_code_dict.values())[0]
                elif "code" in body:
                    # Generic format
                    api_err = str(body["code"])
            except Exception:
                pass

            if e.response.status_code in (401, 403):
                raise UnauthorizedError(f"Unauthorized: HTTP {e.response.status_code}", status_code=e.response.status_code, api_error_code=api_err)
            
            if e.response.status_code in retry_statuses:
                if attempt == max_retries - 1:
                    if e.response.status_code == 429:
                        raise RateLimitError(f"Rate limited after {max_retries} attempts", status_code=e.response.status_code, api_error_code=api_err)
                    raise ConnectorError(f"Server error {e.response.status_code} after {max_retries} attempts", status_code=e.response.status_code, api_error_code=api_err)
                
                delay = base_delay * (2 ** attempt)
                logger.warning(f"HTTP {e.response.status_code}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            
            # Other HTTP errors (e.g., 400, 404) do not retry
            raise ConnectorError(f"HTTP Error: {e.response.status_code}", status_code=e.response.status_code, api_error_code=api_err)
            
        except (httpx.TimeoutException, httpx.RequestError) as e:
            if attempt == max_retries - 1:
                raise ConnectorError(f"Network error after {max_retries} attempts: {e}")
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Network error ({type(e).__name__}). Retrying in {delay}s...")
            await asyncio.sleep(delay)
            
    raise ConnectorError("Max retries exceeded")

class NormalizedRecord(BaseModel):
    source: str
    external_id: str
    stat_date: date
    spend: Decimal
    revenue: Decimal
    currency: str
    clicks: int = Field(default=0, ge=0)
    impressions: int = Field(default=0, ge=0)
    conversions: Decimal = Field(default_factory=lambda: Decimal("0"), ge=Decimal("0"))

class NormalizedAdAccount(BaseModel):
    platform: str
    external_account_id: str
    status: str
    name: str | None = None

class Connector(ABC):
    def __init__(self, config: Any, timeout: int = 30):
        self.config = config
        self.timeout = timeout
        self.register_secret = lambda s: None

    @abstractmethod
    async def test_connection(self) -> bool:
        pass

    @abstractmethod
    async def fetch_campaigns(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_metrics(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        pass

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetches raw data from the external source."""
        raise NotImplementedError("fetch() must be implemented by the connector")

    @abstractmethod
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        """Converts raw data into a normalized internal format."""
        pass

    @abstractmethod
    async def upsert(self, session: AsyncSession, normalized_data: List[NormalizedRecord]) -> None:
        """
        Upserts the normalized data into the database.
        Upsert should find CampaignRun via ExternalCampaignMapping (not by note).
        All connectors should rely on the scheduler to provide the mapped campaign_run_id if necessary, or do the mapping inside upsert.
        """
        pass

    async def fetch_ad_accounts(self) -> List[Dict[str, Any]]:
        """Optional: Fetches raw ad account data."""
        return []

    def normalize_ad_accounts(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedAdAccount]:
        """Optional: Converts raw ad account data into normalized format."""
        return []

    async def upsert_ad_accounts(self, session: AsyncSession, normalized_data: List[NormalizedAdAccount]) -> None:
        """Upserts normalized ad accounts into the database."""
        from app.db.models.campaigns import AdAccount
        
        for record in normalized_data:
            stmt = select(AdAccount).where(
                and_(
                    AdAccount.company_id == self.config.company_id,
                    AdAccount.platform == record.platform,
                    AdAccount.external_account_id == record.external_account_id,
                    AdAccount.deleted_at.is_(None)
                )
            )
            res = await session.execute(stmt)
            acc = res.scalars().first()
            if acc:
                if acc.status != record.status:
                    acc.status = record.status
            else:
                new_acc = AdAccount(
                    company_id=self.config.company_id,
                    platform=record.platform,
                    external_account_id=record.external_account_id,
                    status=record.status
                )
                session.add(new_acc)
    
    async def sync(self, session: AsyncSession) -> None:
        """Orchestrates the entire sync process."""
        # 1. Sync ad accounts (if supported)
        raw_accounts = await self.fetch_ad_accounts()
        if raw_accounts:
            norm_accounts = self.normalize_ad_accounts(raw_accounts)
            await self.upsert_ad_accounts(session, norm_accounts)

        # 2. Sync stats
        raw_data = await self.fetch()
        normalized = self.normalize(raw_data)
        await self.upsert(session, normalized)