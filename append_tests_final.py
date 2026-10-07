with open('04-backend/tests/test_live_connector_validation.py', 'a', encoding='utf-8') as f:
    f.write('''
def test_google_test_account_empty_metrics_exit_0(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["validate_live_connectors.py", "--platform", "google_ads"])
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

    import pytest
    from scripts.validate_live_connectors import main
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert "empty_result" in captured.out
    assert "auth_path_validated" in captured.out
    assert "is_test_account" in captured.out

def test_google_production_account_empty_metrics_exit_2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["validate_live_connectors.py", "--platform", "google_ads"])
    monkeypatch.setenv("LIVE_CONNECTOR_VALIDATION", "1")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "mock_client_id_123")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "mock_client_secret_abc")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "1//token")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "mock_customer_id_999")

    class MockResp:
        def raise_for_status(self): pass
        def json(self): return {"results": [{"customer": {"testAccount": False}}]}
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

    import pytest
    from scripts.validate_live_connectors import main
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "empty_result" in captured.out

def test_google_developer_token_warning(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["validate_live_connectors.py", "--platform", "google_ads"])
    monkeypatch.setenv("LIVE_CONNECTOR_VALIDATION", "1")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "mock_client_id_123")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "mock_client_secret_abc")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "1//token")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "mock_customer_id_999")
    monkeypatch.setenv("GOOGLE_ADS_DEVELOPER_TOKEN", "super_secret_dev_token_999")

    class MockConnector:
        def __init__(self, *args, **kwargs):
            raise Exception("Stop execution")
    monkeypatch.setattr("scripts.validate_live_connectors.GoogleAdsConnector", MockConnector)

    import pytest
    from scripts.validate_live_connectors import main
    with pytest.raises(SystemExit) as exc:
        main()
        
    captured = capsys.readouterr()
    assert "super_secret_dev_token_999" not in captured.out
    assert "super_secret_dev_token_999" not in captured.err
    assert "GOOGLE_ADS_DEVELOPER_TOKEN is set but its value is masked" in captured.err

def test_google_init_error_masked(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["validate_live_connectors.py", "--platform", "google_ads"])
    monkeypatch.setenv("LIVE_CONNECTOR_VALIDATION", "1")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_ID", "mock_client_id_123")
    monkeypatch.setenv("GOOGLE_ADS_CLIENT_SECRET", "mock_client_secret_abc")
    monkeypatch.setenv("GOOGLE_ADS_REFRESH_TOKEN", "1//token")
    monkeypatch.setenv("GOOGLE_ADS_CUSTOMER_ID", "mock_customer_id_999")

    class MockConnector:
        def __init__(self, *args, **kwargs):
            raise Exception("Sensitive DB traceback detail here")
    monkeypatch.setattr("scripts.validate_live_connectors.GoogleAdsConnector", MockConnector)

    import pytest
    from scripts.validate_live_connectors import main
    with pytest.raises(SystemExit) as exc:
        main()
        
    captured = capsys.readouterr()
    assert "Sensitive DB traceback detail here" not in captured.out
    assert "Sensitive DB traceback detail here" not in captured.err
    assert "Exception text masked for security" in captured.out

def test_google_cloud_project_not_approved_hint(monkeypatch):
    from scripts.validate_live_connectors import map_google_error
    class MockError(Exception):
        def __init__(self):
            self.api_error_code = "CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION"
    err = map_google_error(MockError())
    assert err.category == "access_level_insufficient"
    assert "Ensure you have applied for Explorer access" in err.message

''')
print("Tests cleanly appended.")
