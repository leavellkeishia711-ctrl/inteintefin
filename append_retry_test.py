with open('04-backend/tests/test_live_connector_validation.py', 'a', encoding='utf-8') as f:
    f.write('''

def test_google_test_account_timeout_and_retry(monkeypatch, capsys):
    import sys
    import httpx
    import asyncio
    monkeypatch.setattr(sys, "argv", ["validate_live_connectors.py", "--platform", "google_ads", "--timeout", "13"])
    monkeypatch.setenv("LIVE_CONNECTOR_VALIDATION", "1")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "mock_client_id_123")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "mock_client_secret_abc")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "1//token")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "mock_customer_id_999")

    class MockResp:
        def raise_for_status(self): pass
        def json(self): return {"results": [{"customer": {"testAccount": True}}]}
    async def mock_post(*args, **kwargs):
        return MockResp()
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    class MockGetResp:
        def raise_for_status(self): pass
        def json(self): return {"resourceNames": ["customers/mock_customer_id_999"]}
    async def mock_get(*args, **kwargs):
        return MockGetResp()
    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    class MockConnector:
        def __init__(self, *args, **kwargs):
            self.customer_id = "mock_customer_id_999"
            self.login_customer_id = None
            self.register_secret = lambda x: None
        def _get_headers(self): return {}
        async def test_connection(self): return True
        async def fetch_ad_accounts(self): return [{"customer": {"id": "mock_customer_id_999", "currencyCode": "USD"}}]
        def normalize_ad_accounts(self, a): pass
        async def fetch_campaigns(self): return [{"campaign": {"id": 1}}]
        async def fetch_metrics(self, *args, **kwargs): return []
    monkeypatch.setattr("scripts.validate_live_connectors.GoogleAdsConnector", MockConnector)

    # We need to track the timeout passed to AsyncClient
    original_client = httpx.AsyncClient
    client_kwargs = []
    
    class MockClient(original_client):
        def __init__(self, *args, **kwargs):
            client_kwargs.append(kwargs)
            super().__init__(*args, **kwargs)
            
        async def post(self, url, **kwargs):
            if "googleAds:search" in url:
                # Mock a 503 on the first try, then success on second try
                if not getattr(self, "failed_once", False):
                    self.failed_once = True
                    resp = httpx.Response(503, request=httpx.Request("POST", url))
                    raise httpx.HTTPStatusError("503", request=resp.request, response=resp)
            return await mock_post(url, **kwargs)
            
    monkeypatch.setattr("httpx.AsyncClient", MockClient)
    # Speed up the retry delay for the test
    monkeypatch.setattr("asyncio.sleep", lambda *args, **kwargs: asyncio.sleep(0))

    import pytest
    from scripts.validate_live_connectors import main
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "empty_result" in captured.out
    
    # Assert timeout was passed
    timeouts = [k.get("timeout") for k in client_kwargs if "timeout" in k]
    assert 13.0 in timeouts or 13 in timeouts, f"Timeouts found: {timeouts}"

''')
print("Retry test appended.")
