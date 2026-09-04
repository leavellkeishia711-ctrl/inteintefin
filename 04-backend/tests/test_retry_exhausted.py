import pytest
import httpx
from app.connectors.base import ConnectorError
from app.connectors.base import with_retry

pytestmark = pytest.mark.asyncio

async def test_retry_exhausted():
    attempts = 0
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        req = httpx.Request("GET", "http://test")
        resp = httpx.Response(503, request=req)
        raise httpx.HTTPStatusError("503", request=req, response=resp)

    with pytest.raises(ConnectorError):
        await with_retry(fetch_data, max_retries=2, base_delay=0)
        
    assert attempts == 2
