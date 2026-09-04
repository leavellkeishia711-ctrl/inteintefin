import pytest
import time
import httpx
from app.connectors.base import with_retry, RateLimitError

pytestmark = pytest.mark.asyncio

async def test_retry_429():
    attempts = 0
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            req = httpx.Request("GET", "http://test")
            resp = httpx.Response(429, request=req)
            raise httpx.HTTPStatusError("Rate limit", request=req, response=resp)
        return "success"

    start = time.time()
    res = await with_retry(fetch_data, max_retries=2, base_delay=1)
    end = time.time()
    
    assert res == "success"
    assert attempts == 2
    assert end - start >= 1.0 # Due to retry_after/backoff
