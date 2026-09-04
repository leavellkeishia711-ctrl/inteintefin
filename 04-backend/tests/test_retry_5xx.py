import pytest
from app.connectors.base import with_retry, ConnectorError

pytestmark = pytest.mark.asyncio

async def test_retry_5xx():
    attempts = 0
    @with_retry(max_retries=2, base_delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise ConnectorError("502 Bad Gateway", status_code=502)
        return "success"

    res = await fetch_data()
    assert res == "success"
    assert attempts == 2
