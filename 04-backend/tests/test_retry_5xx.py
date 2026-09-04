import pytest
import httpx
from app.connectors.base import with_retry

pytestmark = pytest.mark.asyncio

async def test_retry_5xx():
    attempts = 0
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            req = httpx.Request("GET", "http://test")
            resp = httpx.Response(502, request=req)
            raise httpx.HTTPStatusError("502", request=req, response=resp)
        return "success"

    res = await with_retry(fetch_data, max_retries=2, base_delay=0)
    assert res == "success"
    assert attempts == 2
