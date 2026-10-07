import asyncio
import httpx

async def fetch_test_account_status():
    async with httpx.AsyncClient(timeout=13.0) as client:
        url = "https://googleads.googleapis.com/v25/customers/mock_customer_id_999/googleAds:search"
        res = await client.post(url, json={})
        res.raise_for_status()
        return res

async def main():
    from app.connectors.base import with_retry
    
    post_calls = {"count": 0}
    class MockResp:
        def raise_for_status(self): pass
        def json(self): return {"results": [{"customer": {"testAccount": True}}]}

    async def mock_post(self_obj, url, **kwargs):
        if "googleAds:search" in url:
            post_calls["count"] += 1
            if post_calls["count"] == 1:
                req = httpx.Request("POST", url)
                resp = httpx.Response(503, request=req)
                raise httpx.HTTPStatusError("503", request=req, response=resp)
        return MockResp()

    import httpx
    # monkeypatch
    original_post = httpx.AsyncClient.post
    httpx.AsyncClient.post = mock_post

    try:
        await with_retry(fetch_test_account_status, max_retries=3, base_delay=0)
    finally:
        httpx.AsyncClient.post = original_post

asyncio.run(main())
