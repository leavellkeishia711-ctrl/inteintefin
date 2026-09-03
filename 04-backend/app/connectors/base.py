from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel
import uuid
from decimal import Decimal
from datetime import date

class NormalizedRecord(BaseModel):
    source: str
    external_id: str
    stat_date: date
    spend: Decimal
    revenue: Decimal
    currency: str

class Connector(ABC):
    def __init__(self, config: Any):
        self.config = config

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetches raw data from the external source."""
        pass

    @abstractmethod
    def normalize(self, raw_data: List[Dict[str, Any]]) -> List[NormalizedRecord]:
        """Converts raw data into a normalized internal format."""
        pass

    @abstractmethod
    async def upsert(self, normalized_data: List[NormalizedRecord]) -> None:
        """Upserts the normalized data into the database."""
        pass
    
    async def sync(self) -> None:
        """Orchestrates the entire sync process."""
        raw_data = await self.fetch()
        normalized = self.normalize(raw_data)
        await self.upsert(normalized)
