import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List
import logging
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, and_
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
            # Cube with invalid date goes to skipped, count its children
            skipped += len(cube_date.findall("ns:Cube", ECB_NAMESPACE))
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
            async with client.stream("GET", ECB_URL, timeout=10.0, follow_redirects=False) as res:
                if res.status_code != 200:
                    raise ValueError(f"HTTP error: expected 200, got {res.status_code}")
                
                content_length = res.headers.get("Content-Length")
                if content_length and int(content_length) > 2 * 1024 * 1024:
                    raise ValueError("ECB payload too large (>2MB)")
                    
                chunks = []
                size = 0
                async for chunk in res.aiter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size > 2 * 1024 * 1024:
                        raise ValueError("ECB payload too large (>2MB) during streaming")
                        
                return b"".join(chunks)
            
    return await with_retry(_do_fetch, max_retries=3, base_delay=1)


async def sync_ecb_rates(session: AsyncSession) -> Dict[str, Any]:
    try:
        xml_content = await fetch_ecb_xml()
    except Exception as e:
        logger.error(f"Failed to fetch ECB rates: {e}")
        return {"dates": 0, "fetched": 0, "inserted": 0, "unchanged": 0, "conflicts": 0, "skipped": 0}
        
    results, dates_count, skipped = parse_ecb_xml(xml_content)
    
    if len(results) == 0:
        logger.error("0 valid rates parsed from ECB. Failing the task without writing.")
        return {"dates": dates_count, "fetched": 0, "inserted": 0, "unchanged": 0, "conflicts": 0, "skipped": skipped}
        
    inserted = 0
    unchanged = 0
    conflicts = 0
    
    values = []
    for r in results:
        values.append({
            "rate_date": r["rate_date"],
            "from_currency": "EUR",
            "to_currency": r["to_currency"],
            "rate": r["rate"],
            "source": "ecb"
        })
        
    stmt = insert(FxRate).values(values).returning(
        FxRate.rate_date, FxRate.to_currency
    )
    stmt = stmt.on_conflict_do_nothing(
        constraint="uq_fx_rate_date_currencies_source"
    )
    
    try:
        res = await session.execute(stmt)
        inserted_rows = res.all()
        inserted = len(inserted_rows)
        
        # Calculate conflicts and unchanged
        inserted_keys = {(row.rate_date, row.to_currency) for row in inserted_rows}
        
        not_inserted = [v for v in values if (v["rate_date"], v["to_currency"]) not in inserted_keys]
        if not_inserted:
            # We need to query the database to compare the rates
            conditions = []
            for v in not_inserted:
                conditions.append(
                    and_(
                        FxRate.rate_date == v["rate_date"],
                        FxRate.to_currency == v["to_currency"]
                    )
                )
            
            # Group conditions by chunks to avoid huge queries, though max ~90*30=2700 is fine
            # We will use an IN clause combined or an OR clause
            from sqlalchemy import tuple_
            tuples = [(v["rate_date"], "EUR", v["to_currency"], "ecb") for v in not_inserted]
            
            # Fetch existing rows
            check_stmt = select(FxRate.rate_date, FxRate.to_currency, FxRate.rate).where(
                tuple_(FxRate.rate_date, FxRate.from_currency, FxRate.to_currency, FxRate.source).in_(tuples)
            )
            
            check_res = await session.execute(check_stmt)
            existing_rows = check_res.all()
            
            existing_map = {(r.rate_date, r.to_currency): r.rate for r in existing_rows}
            
            for v in not_inserted:
                key = (v["rate_date"], v["to_currency"])
                if key in existing_map:
                    if existing_map[key] == v["rate"]:
                        unchanged += 1
                    else:
                        conflicts += 1
                        
    except Exception as e:
        logger.error(f"Failed to insert ECB rates: {e}")
        raise
        
    out = {
        "dates": dates_count,
        "fetched": len(results),
        "inserted": inserted,
        "unchanged": unchanged,
        "conflicts": conflicts,
        "skipped": skipped
    }
    logger.info(f"ECB FX Sync: {out}")
    return out
