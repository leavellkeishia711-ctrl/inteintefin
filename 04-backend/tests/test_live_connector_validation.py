import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Add scripts to path to import the script for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import validate_live_connectors
from validate_live_connectors import (
    validate_google_ads,
    validate_tiktok_ads,
    sanitize_exception,
    main
)

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {}, clear=True):
        yield

def test_live_validation_requires_explicit_opt_in(mock_env, capsys):
    with patch("sys.exit") as mock_exit:
        try:
            main()
        except SystemExit:
            pass
        mock_exit.assert_any_call(1)
        captured = capsys.readouterr()
        assert "LIVE_CONNECTOR_VALIDATION=1" in captured.err

@pytest.mark.asyncio
async def test_google_live_validation_reads_env_without_logging_secrets(mock_env, capsys):
    os.environ["LIVE_CONNECTOR_VALIDATION"] = "1"
    os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = "super_secret_dev_token_value_that_should_not_leak"
    os.environ["GOOGLE_ADS_CLIENT_ID"] = "client_id_12345"
    os.environ["GOOGLE_ADS_CLIENT_SECRET"] = "client_secret_12345"
    os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = "refresh_token_12345"
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = Exception("Failed with super_secret_dev_token_value_that_should_not_leak!")
        with patch("sys.exit"):
            await validate_google_ads("cust-123")
            captured = capsys.readouterr()
            assert "super_secret_dev_token_value_that_should_not_leak" not in captured.out
            assert "***MASKED***" in captured.out

@pytest.mark.asyncio
async def test_google_live_validation_sanitizes_auth_failure(mock_env, capsys):
    os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = "dev"
    os.environ["GOOGLE_ADS_CLIENT_ID"] = "client"
    os.environ["GOOGLE_ADS_CLIENT_SECRET"] = "secret"
    os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = "refresh"
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value.status_code = 401
        with patch("sys.exit"):
            await validate_google_ads("cust-123")
            captured = capsys.readouterr()
            out = json.loads(captured.out)
            assert out["status"] == "fail"
            assert "UnauthorizedError" in out["error"]

@pytest.mark.asyncio
async def test_google_live_validation_validates_decimal_metrics(mock_env, capsys):
    os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = "dev"
    os.environ["GOOGLE_ADS_CLIENT_ID"] = "client"
    os.environ["GOOGLE_ADS_CLIENT_SECRET"] = "secret"
    os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = "refresh"
    
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code
        def json(self): return self._json_data
        def raise_for_status(self): pass
            
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = [
            MockResponse({"access_token": "acc"}),
            MockResponse({"results": [{"customer": {"currencyCode": "USD"}}]}),
            MockResponse({"results": [{"metrics": {"costMicros": 1000000, "conversions": "1.5"}}]})
        ]
        
        await validate_google_ads("1234567890")
        captured = capsys.readouterr()
        out = json.loads(captured.out)
        assert out["status"] == "pass"
        assert out["currency"] == "USD"
        assert out["rows_fetched"] == 1

@pytest.mark.asyncio
async def test_google_live_validation_rejects_negative_metrics(mock_env, capsys):
    os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"] = "dev"
    os.environ["GOOGLE_ADS_CLIENT_ID"] = "client"
    os.environ["GOOGLE_ADS_CLIENT_SECRET"] = "secret"
    os.environ["GOOGLE_ADS_REFRESH_TOKEN"] = "refresh"
    
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code
        def json(self): return self._json_data
        def raise_for_status(self): pass
            
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = [
            MockResponse({"access_token": "acc"}),
            MockResponse({"results": [{"customer": {"currencyCode": "USD"}}]}),
            MockResponse({"results": [{"metrics": {"costMicros": -500}}]})
        ]
        
        with patch("sys.exit"):
            await validate_google_ads("1234567890")
            captured = capsys.readouterr()
            out = json.loads(captured.out)
            assert out["status"] == "fail"
            assert out["error"] == "ValueError"
            assert "Negative cost found" in out["message"]

@pytest.mark.asyncio
async def test_tiktok_live_validation_reads_env_without_logging_secrets(mock_env, capsys):
    os.environ["TIKTOK_ACCESS_TOKEN"] = "super_secret_tiktok_token"
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("Failed with super_secret_tiktok_token!")
        with patch("sys.exit"):
            await validate_tiktok_ads("adv-123")
            captured = capsys.readouterr()
            assert "super_secret_tiktok_token" not in captured.out
            assert "***MASKED***" in captured.out

@pytest.mark.asyncio
async def test_tiktok_live_validation_sanitizes_auth_failure(mock_env, capsys):
    os.environ["TIKTOK_ACCESS_TOKEN"] = "tok"
    
    with patch("httpx.AsyncClient.get") as mock_get:
        class MockResponse:
            status_code = 401
        mock_get.return_value = MockResponse()
        with patch("sys.exit"):
            await validate_tiktok_ads("adv-123")
            captured = capsys.readouterr()
            out = json.loads(captured.out)
            assert out["status"] == "fail"
            assert "UnauthorizedError" in out["error"]

@pytest.mark.asyncio
async def test_tiktok_live_validation_validates_report_schema(mock_env, capsys):
    os.environ["TIKTOK_ACCESS_TOKEN"] = "tok"
    
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code
        def json(self): return self._json_data
        def raise_for_status(self): pass
            
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [
            MockResponse({"code": 0, "data": {"list": [{"currency": "EUR"}]}}),
            MockResponse({"code": 0, "data": {"list": [{"metrics": {"spend": "10.5", "clicks": "5", "impressions": "100", "conversion": "1.0"}}]}})
        ]
        
        await validate_tiktok_ads("1234567890")
        captured = capsys.readouterr()
        out = json.loads(captured.out)
        assert out["status"] == "pass"
        assert out["currency"] == "EUR"
        assert out["rows_fetched"] == 1

@pytest.mark.asyncio
async def test_tiktok_live_validation_validates_decimal_metrics(mock_env, capsys):
    os.environ["TIKTOK_ACCESS_TOKEN"] = "tok"
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self._json_data = json_data
            self.status_code = status_code
        def json(self): return self._json_data
        def raise_for_status(self): pass
            
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = [
            MockResponse({"code": 0, "data": {"list": [{"currency": "EUR"}]}}),
            MockResponse({"code": 0, "data": {"list": [{"metrics": {"spend": "-10.5"}}]}})
        ]
        
        with patch("sys.exit"):
            await validate_tiktok_ads("1234567890")
            captured = capsys.readouterr()
            out = json.loads(captured.out)
            assert out["status"] == "fail"
            assert out["error"] == "ValueError"
            assert "Negative spend found" in out["message"]

def test_validation_never_persists_raw_payload():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/validate_live_connectors.py'))
    with open(script_path, 'r') as f:
        content = f.read()
    assert "open(" not in content, "Script should not write to files"
    assert "write(" not in content, "Script should not write to files"
    assert "print(dev_token)" not in content
    assert "print(access_token)" not in content

def test_validation_output_contains_no_credentials():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/validate_live_connectors.py'))
    with open(script_path, 'r') as f:
        content = f.read()
    assert 'print(f"{access_token}"' not in content
    assert "print(client_secret)" not in content

def test_validation_uses_bounded_date_range():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/validate_live_connectors.py'))
    with open(script_path, 'r') as f:
        content = f.read()
    assert "timedelta(days=1)" in content
    assert "LIMIT 10" in content

def test_validation_is_read_only():
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts/validate_live_connectors.py'))
    with open(script_path, 'r') as f:
        content = f.read()
    assert "mutate" not in content.lower()
    assert "update " not in content.lower()
    assert "insert into" not in content.lower()
    assert "delete " not in content.lower()
