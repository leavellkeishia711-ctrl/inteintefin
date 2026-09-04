import pytest
import time
from app.connectors.base import with_retry, RateLimitError

pytestmark = pytest.mark.asyncio

async def test_retry_429():
    attempts = 0
    @with_retry(max_retries=2, base_delay=0)
    async def fetch_data():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise RateLimitError("Rate limit", retry_after=1)
        return "success"

    start = time.time()
    res = await fetch_data()
    end = time.time()
    
    assert res == "success"
    assert attempts == 2
    assert end - start >= 1.0 # Due to retry_after=1
