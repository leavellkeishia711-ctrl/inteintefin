import pytest
from app.connectors.base import with_retry, ConnectorError

pytestmark = pytest.mark.asyncio

async def test_retry_exhausted():
    attempts = 0
    @with_retry(max_retries=2, base_delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        raise ConnectorError("503 Service Unavailable", status_code=503)

    with pytest.raises(ConnectorError):
        await fetch_data()
        
    assert attempts == 3 # Initial + 2 retries
