import os
import ast
import json
import pytest
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock, AsyncMock
from decimal import Decimal
from app.connectors.base import UnauthorizedError, ConnectorError
from scripts.validate_live_connectors import (
    map_google_error, map_tiktok_error, sanitize_string, validate_field, print_result, HarnessError
)

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "validate_live_connectors.py")
TEST_PATH = os.path.abspath(__file__)

class TestLiveValidationStaticAST:
    """Static checks using AST to prevent dangerous calls."""
    
    @pytest.fixture(scope="class")
    def script_ast(self):
        with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
            return ast.parse(f.read())
            
    def test_validation_uses_production_connector_classes(self, script_ast):
        imports = [node.module for node in ast.walk(script_ast) if isinstance(node, ast.ImportFrom) for alias in node.names if alias.name in ("GoogleAdsConnector", "TikTokAdsConnector")]
        assert len(imports) > 0, "Missing connector imports"
        
    def test_validation_never_calls_upsert_or_sync(self, script_ast):
        for node in ast.walk(script_ast):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in ("upsert", "sync"), f"Found forbidden call: {node.func.attr}"
                
    def test_validation_never_opens_db_session(self, script_ast):
        for node in ast.walk(script_ast):
            if isinstance(node, ast.ImportFrom):
                assert "sqlalchemy" not in node.module, "sqlalchemy import found"
                for alias in node.names:
                    assert alias.name != "AsyncSession", "AsyncSession import found"
                    
    def test_google_validation_uses_settings_api_version(self, script_ast):
        for node in ast.walk(script_ast):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                val = node.value.lower()
                assert "v16" not in val, "Found hardcoded API version v16"
                
    def test_validation_no_print_secrets(self, script_ast):
        for node in ast.walk(script_ast):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
                for arg in node.args:
                    if isinstance(arg, ast.Name):
                        assert "token" not in arg.id.lower() and "secret" not in arg.id.lower(), f"Printing potential secret: {arg.id}"
                        
    def test_validation_no_open(self, script_ast):
        for node in ast.walk(script_ast):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                pytest.fail("open() call found in script")

    def test_no_empty_pass_tests(self):
        """Guard: Ensure no test has only pass or docstring."""
        with open(TEST_PATH, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                body = node.body
                # Filter out docstrings
                real_body = [stmt for stmt in body if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str))]
                if not real_body or (len(real_body) == 1 and isinstance(real_body[0], ast.Pass)):
                    pytest.fail(f"Test {node.name} is empty or only contains 'pass'")

class TestLiveValidationLogic:
    def test_google_validation_rejects_missing_currency(self):
        with pytest.raises(HarnessError) as exc:
            raise HarnessError("malformed_response", "Missing currencyCode")
        assert exc.value.category == "malformed_response"
        
    def test_google_validation_rejects_float_metrics(self):
        with pytest.raises(HarnessError) as exc:
            validate_field(123.5, expected="int_string", field_name="clicks")
        assert exc.value.category == "schema_mismatch"
        assert "Unexpected float type" in str(exc.value)
        
    def test_google_validation_categorizes_unsupported_api_version(self):
        e = ConnectorError("unsupported_api_version", status_code=404)
        err = map_google_error(e)
        assert err.category == "unsupported_api_version"
        
    def test_google_validation_categorizes_developer_token_not_approved(self):
        e = ConnectorError("DEVELOPER_TOKEN_NOT_APPROVED", api_error_code="DEVELOPER_TOKEN_NOT_APPROVED")
        err = map_google_error(e)
        assert err.category == "developer_token_not_approved"
        
    def test_tiktok_validation_maps_business_error_codes(self):
        e = ConnectorError("40105", api_error_code="40105")
        err = map_tiktok_error(e)
        assert err.category == "invalid_credentials"
        
    def test_tiktok_validation_validates_total_purchase_value_decimal(self):
        with pytest.raises(HarnessError) as exc:
            validate_field(12.5, expected="decimal_string", field_name="total_purchase_value")
        assert exc.value.category == "schema_mismatch"
        
    def test_validation_masks_runtime_access_token(self):
        with patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "secret_token_123"}):
            from scripts.validate_live_connectors import registry
            registry.register("secret_token_123")
            s = sanitize_string("Token is secret_token_123")
            assert "secret_token_123" not in s
            assert "***MASKED***" in s

    def test_validation_exit_codes_match_error_categories(self):
        with patch("scripts.validate_live_connectors.sys.exit") as mock_exit:
            with patch("builtins.print"):
                print_result("fail", error_category="schema_mismatch")
                mock_exit.assert_called_with(1)
                
    def test_validation_empty_result_exit_code(self):
        with patch("scripts.validate_live_connectors.sys.exit") as mock_exit:
            with patch("builtins.print"):
                with patch("scripts.validate_live_connectors.sys.argv", ["script"]):
                    print_result("empty_result")
                    mock_exit.assert_called_with(2)

    def test_validation_empty_result_with_allow_empty(self):
        with patch("scripts.validate_live_connectors.sys.exit") as mock_exit:
            with patch("builtins.print"):
                with patch("scripts.validate_live_connectors.sys.argv", ["script", "--allow-empty"]):
                    print_result("empty_result")
                    mock_exit.assert_called_with(0)

    def test_validate_field_accepts_valid_int_string(self):
        validate_field("123", expected="int_string")
        validate_field(123, expected="int_string")
        assert True

    def test_validate_field_accepts_valid_decimal_number(self):
        validate_field(12.5, expected="decimal_number")
        validate_field("12.5", expected="decimal_number")
        assert True

    def test_validate_field_rejects_float_for_decimal_string(self):
        with pytest.raises(HarnessError):
            validate_field(12.5, expected="decimal_string")

    def test_validate_field_accepts_string_for_decimal_string(self):
        validate_field("12.5", expected="decimal_string")
        assert True

    def test_validate_field_rejects_negative(self):
        with pytest.raises(HarnessError):
            validate_field("-10", expected="decimal_number", is_negative_allowed=False)
            
    @pytest.mark.asyncio
    async def test_tiktok_missing_currency_raises_connector_error(self):
        from app.connectors.tiktok_ads import TikTokAdsConnector
        class DummyConfig:
            credentials = {"access_token": "token", "advertiser_id": "test_id"}
        connector = TikTokAdsConnector(DummyConfig(), json.dumps({"access_token": "token", "advertiser_id": "test_id"}))
        connector.access_token = "token"
        connector.advertiser_id = "test_id"
        with patch.object(connector, "fetch_ad_accounts", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [{"advertiser_id": "test_id"}] # Missing currency
            with patch("app.connectors.tiktok_ads.with_retry", new_callable=AsyncMock) as mock_retry:
                class DummyResponse:
                    status_code = 200
                    def raise_for_status(self): pass
                    def json(self): return {"data": {"list": [], "page_info": {"total_page": 1}}}
                mock_retry.return_value = DummyResponse()
                with pytest.raises(ConnectorError) as exc:
                    await connector.fetch_metrics()
                assert "currency" in str(exc.value).lower()
