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

    # Track how many times post was called
    post_calls = {"count": 0}
    async def mock_post(self_obj, url, **kwargs):
        if "googleAds:search" in url:
            post_calls["count"] += 1
            if post_calls["count"] == 1:
                resp = httpx.Response(503, request=httpx.Request("POST", url))
                raise httpx.HTTPStatusError("503", request=resp.request, response=resp)
        return MockResp()

    class MockGetResp:
        def raise_for_status(self): pass
        def json(self): return {"resourceNames": ["customers/mock_customer_id_999"]}
    async def mock_get(self_obj, url, **kwargs):
        return MockGetResp()
        
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
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

    original_init = httpx.AsyncClient.__init__
    client_timeouts = []
    def mock_init(self_obj, *args, **kwargs):
        if "timeout" in kwargs:
            client_timeouts.append(kwargs["timeout"])
        original_init(self_obj, *args, **kwargs)
        
    monkeypatch.setattr("httpx.AsyncClient.__init__", mock_init)
    monkeypatch.setattr("asyncio.sleep", lambda *args, **kwargs: asyncio.sleep(0))

    import pytest
    from scripts.validate_live_connectors import main
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "empty_result" in captured.out
    
    assert post_calls["count"] == 2
    assert 13.0 in client_timeouts or 13 in client_timeouts
''')
