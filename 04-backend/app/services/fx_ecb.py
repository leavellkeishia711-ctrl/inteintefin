import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List
import logging
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from app.db.models.finance import FxRate
from app.connectors.base import with_retry

logger = logging.getLogger(__name__)

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
ECB_NAMESPACE = {"ns": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

def parse_ecb_xml(xml_content: bytes) -> tuple[List[Dict[str, Any]], int, int]:
    skipped = 0
    results = []
    dates_set = set()
    
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        logger.error("Failed to parse ECB XML.")
        return [], 0, 0
        
    for cube_date in root.findall(".//ns:Cube[@time]", ECB_NAMESPACE):
        time_str = cube_date.attrib.get("time")
        try:
            rate_date = datetime.strptime(time_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
            
        dates_set.add(rate_date)
        
        for cube_rate in cube_date.findall("ns:Cube", ECB_NAMESPACE):
            currency = cube_rate.attrib.get("currency", "")
            rate_str = cube_rate.attrib.get("rate", "")
            
            if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
                skipped += 1
                continue
                
            try:
                rate = Decimal(rate_str)
                if rate <= 0:
                    skipped += 1
                    continue
            except (InvalidOperation, TypeError):
                skipped += 1
                continue
                
            results.append({
                "rate_date": rate_date,
                "to_currency": currency,
                "rate": rate
            })
            
    return results, len(dates_set), skipped


async def fetch_ecb_xml() -> bytes:
    async def _do_fetch():
        async with httpx.AsyncClient() as client:
            res = await client.get(ECB_URL, timeout=10.0, follow_redirects=False)
            res.raise_for_status()
            
            content_length = res.headers.get("Content-Length")
            if content_length and int(content_length) > 2 * 1024 * 1024:
                raise ValueError("ECB payload too large")
                
            content = res.content
            if len(content) > 2 * 1024 * 1024:
                raise ValueError("ECB payload too large")
                
            return res
            
    response = await with_retry(_do_fetch, max_retries=3, base_delay=1)
    return response.content


async def sync_ecb_rates(session: AsyncSession) -> Dict[str, Any]:
    try:
        xml_content = await fetch_ecb_xml()
    except Exception as e:
        logger.error(f"Failed to fetch ECB rates: {e}")
        return {"dates": 0, "fetched": 0, "inserted": 0, "conflicts": 0, "skipped": 0}
        
    results, dates_count, skipped = parse_ecb_xml(xml_content)
    if not dates_count:
        logger.error("No valid dates found in ECB payload.")
        return {"dates": 0, "fetched": 0, "inserted": 0, "conflicts": 0, "skipped": 0}
        
    inserted = 0
    conflicts = 0
    
    if results:
        values = []
        for r in results:
            values.append({
                "rate_date": r["rate_date"],
                "from_currency": "EUR",
                "to_currency": r["to_currency"],
                "rate": r["rate"],
                "source": "ecb"
            })
            
        stmt = insert(FxRate).values(values)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_fx_rate_date_currencies_source"
        )
        
        try:
            res = await session.execute(stmt)
            inserted = res.rowcount
            conflicts = len(values) - inserted
        except Exception as e:
            logger.error(f"Failed to insert ECB rates: {e}")
            raise # Let it bubble up so transaction rolls back automatically
            
    out = {
        "dates": dates_count,
        "fetched": len(results),
        "inserted": inserted,
        "conflicts": conflicts,
        "skipped": skipped
    }
    logger.info(f"ECB FX Sync: {out}")
    return out
