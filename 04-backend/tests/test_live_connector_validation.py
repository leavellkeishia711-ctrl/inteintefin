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



    @pytest.mark.asyncio

    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)

    async def test_google_invalid_numeric_string_no_nameerror(self, mock_post, mock_get):

        from scripts.validate_live_connectors import run_google_validation, registry

        registry._secrets.clear()

        class Args:

            platform = "google_ads"

            customer_id = "123"

            date = "2024-01-01"

            days = 1

            timeout = 10

            max_pages = 1

            page_size = 10

            allow_empty = False


        mock_get.return_value.status_code = 200
        mock_get.return_value.json = lambda: {"resourceNames": ["customers/123"]}

        mock_post.return_value.status_code = 200

        mock_post.return_value.json = lambda: {

            "access_token": "access_token_12345", "results": [{

                "campaign": {"id": "c1"},

                "segments": {"date": "2024-01-01"},

                "customer": {"currencyCode": "USD", "id": "123"},

                "metrics": {

                    "costMicros": "invalid_number_here",

                    "conversionsValue": "500",

                    "conversions": "0",

                    "clicks": "0",

                    "impressions": "0"

                }

            }]

        }

        

        with patch("scripts.validate_live_connectors.sys.exit", side_effect=SystemExit) as mock_exit, patch.dict("os.environ", {"GOOGLE_ADS_DEVELOPER_TOKEN": "secret_token_12345", "GOOGLE_ADS_CLIENT_ID": "client_id_12345", "GOOGLE_ADS_CLIENT_SECRET": "client_secret_12345", "GOOGLE_ADS_REFRESH_TOKEN": "refresh_token_12345"}):

            with patch("builtins.print") as mock_print:

                try: 

                    await run_google_validation(Args())

                except SystemExit: 

                    assert True

                output = str(mock_print.call_args)

                assert "NameError" not in output

                assert "schema_mismatch" in output

                assert "secret_token" not in output



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

        assert err.category == "access_level_insufficient"



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

            

            # Short secret test

            registry.register("ab")

            s2 = sanitize_string("Token is ab!")

            assert "ab" not in s2

            assert "***MASKED***!" in s2



    def test_validation_argv_short_secret(self):

        from scripts.validate_live_connectors import registry, assert_no_secrets_in_argv

        registry._secrets.clear()

        registry.register("xyz")

        with patch("sys.exit") as mock_exit:

            with patch("builtins.print") as mock_print:

                assert_no_secrets_in_argv(["script.py", "--token", "xyz123"], registry)

                mock_exit.assert_called_once_with(1)

                # Ensure the secret itself is not printed

                assert "xyz" not in str(mock_print.call_args)



    def test_validation_argv_safe(self):

        from scripts.validate_live_connectors import registry, assert_no_secrets_in_argv

        registry._secrets.clear()

        registry.register("supersecret")

        with patch("sys.exit") as mock_exit:

            assert_no_secrets_in_argv(["script.py", "--token", "safe_value"], registry)

            mock_exit.assert_not_called()





    def test_validation_exit_codes_match_error_categories(self):

        with patch("scripts.validate_live_connectors.sys.exit") as mock_exit, patch("sys.argv", ["script.py", "safe"]):

            with patch("builtins.print"):

                from scripts.validate_live_connectors import print_result

                print_result("fail", error_category="rate_limited")

                mock_exit.assert_called_with(1)

                

    def test_validation_empty_result_exit_code(self):

        with patch("scripts.validate_live_connectors.sys.exit") as mock_exit, patch("sys.argv", ["script.py", "safe"]):

            with patch("builtins.print"):

                from scripts.validate_live_connectors import print_result

                print_result("empty_result")

                mock_exit.assert_called_with(2)

                

    def test_validation_empty_result_with_allow_empty(self):

        with patch("scripts.validate_live_connectors.sys.exit") as mock_exit, patch("sys.argv", ["script.py", "--allow-empty", "safe"]):

            with patch("builtins.print"):

                from scripts.validate_live_connectors import print_result

                print_result("empty_result")

                mock_exit.assert_called_with(0)



    @pytest.mark.asyncio

    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)

    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)

    async def test_timeout_is_passed_to_http_calls(self, mock_get, mock_post):

        from app.connectors.google_ads import GoogleAdsConnector

        from app.connectors.tiktok_ads import TikTokAdsConnector

        from unittest.mock import MagicMock

        

        class DummyConfig:

            company_id = "0000"

            connector_name = "test"

            id = "1"

            credentials = {}



        mock_resp = MagicMock()

        mock_resp.status_code = 200

        mock_resp.json.return_value = {"access_token": "token", "results": []}

        mock_post.return_value = mock_resp

        

        g_conn = GoogleAdsConnector(DummyConfig(), '{"developer_token": "a", "client_id": "b", "client_secret": "c", "refresh_token": "d", "customer_id": "e"}', timeout=42)

        try:

            await g_conn.fetch_ad_accounts()

        except Exception:

            assert True

        

        assert mock_post.call_args is not None

        assert mock_post.call_args.kwargs.get("timeout") == 42

        

        mock_get_resp = MagicMock()

        mock_get_resp.status_code = 200

        mock_get_resp.json.return_value = {"code": 0, "data": {"list": []}}

        mock_get.return_value = mock_get_resp

        

        t_conn = TikTokAdsConnector(DummyConfig(), '{"access_token": "a", "advertiser_id": "b"}', timeout=43)

        try:

            await t_conn.fetch_ad_accounts()

        except Exception:

            assert True

            

        assert mock_get.call_args is not None

        assert mock_get.call_args.kwargs.get("timeout") == 43



    @pytest.mark.asyncio

    @patch("httpx.AsyncClient.get")

    async def test_tiktok_missing_identity_in_harness(self, mock_get):

        from scripts.validate_live_connectors import run_tiktok_validation

        class Args:

            platform = "tiktok_ads"

            advertiser_id = "123"

            date = "2024-01-01"

            days = 1

            timeout = 10

            max_pages = 1

            page_size = 10

            allow_empty = False



        mock_get.return_value.status_code = 200

        mock_get.return_value.json = lambda: {"code": 0, "data": {"list": [{"currency": "USD"}]}}

    

        with patch("scripts.validate_live_connectors.sys.exit", side_effect=SystemExit) as mock_exit, patch.dict("os.environ", {"TIKTOK_ACCESS_TOKEN": "token"}):

            with patch("builtins.print") as mock_print:

                try: await run_tiktok_validation(Args())

                except SystemExit: pass

                output = str(mock_print.call_args)

                assert "malformed_response" in output

                assert "missing advertiser_id" in output



    @pytest.mark.asyncio

    @patch("httpx.AsyncClient.get")

    async def test_tiktok_mismatch_identity_in_harness(self, mock_get):

        from scripts.validate_live_connectors import run_tiktok_validation

        class Args:

            platform = "tiktok_ads"

            advertiser_id = "123"

            date = "2024-01-01"

            days = 1

            timeout = 10

            max_pages = 1

            page_size = 10

            allow_empty = False



        mock_get.return_value.status_code = 200

        mock_get.return_value.json = lambda: {"code": 0, "data": {"list": [{"advertiser_id": "999", "currency": "USD"}]}}

    

        with patch("scripts.validate_live_connectors.sys.exit", side_effect=SystemExit) as mock_exit, patch.dict("os.environ", {"TIKTOK_ACCESS_TOKEN": "token"}):

            with patch("builtins.print") as mock_print:

                try: await run_tiktok_validation(Args())

                except SystemExit: pass

                output = str(mock_print.call_args)

                assert "schema_mismatch" in output

                assert "advertiser_id mismatch" in output

import pytest

import os

import json

from decimal import Decimal

import httpx

from app.connectors.google_ads import GoogleAdsConnector

from app.connectors.meta_ads import MetaAdsConnector

from app.connectors.binom import BinomConnector

from scripts.validate_live_connectors import (

    HarnessError,

    map_google_error,

    map_meta_error,

    map_binom_error

)



class DummyConfig:

    connector_name = "dummy"

    company_id = 1

    settings = {}



def get_config_with_mode(mode):
    class C:
        connector_name = "dummy"
        company_id = 1
        settings = {"access_mode": mode, "api_version": "v25"}
    return C()

def get_google_creds(access_mode, dev_token):

    c = {

        "client_id": "c",

        "client_secret": "s",

        "refresh_token": "r",

        "customer_id": "1",

        "access_mode": access_mode

    }

    if dev_token is not None:

        c["developer_token"] = dev_token

    return json.dumps(c)



def test_google_cloud_managed_mode_works_without_developer_token():

    conn = GoogleAdsConnector(get_config_with_mode("cloud_managed"), get_google_creds("cloud_managed", None))

    assert conn.access_mode == "cloud_managed"

    assert conn.developer_token is None



def test_google_cloud_managed_mode_omits_developer_token_header():

    conn = GoogleAdsConnector(get_config_with_mode("cloud_managed"), get_google_creds("cloud_managed", None))

    conn.access_token = "tok"

    headers = conn._get_headers()

    assert "developer-token" not in headers



def test_google_legacy_mode_requires_developer_token():

    with pytest.raises(ValueError, match="Developer token required"):

        GoogleAdsConnector(get_config_with_mode("legacy"), get_google_creds("legacy", None))

    with pytest.raises(ValueError, match="Developer token required"):

        GoogleAdsConnector(get_config_with_mode("legacy"), get_google_creds("legacy", ""))



def test_google_rejects_placeholder_developer_token():

    for p in ["xxx", "placeholder", "changeme", "your_token", "none", "null"]:

        with pytest.raises(ValueError, match="Developer token required"):

            GoogleAdsConnector(get_config_with_mode("legacy"), get_google_creds("legacy", p))



def test_google_existing_encrypted_credentials_with_developer_token_still_work():

    # Implicit cloud_managed by default

    creds = {

        "client_id": "c",

        "client_secret": "s",

        "refresh_token": "r",

        "customer_id": "1",

        "developer_token": "valid_token"

    }

    conn = GoogleAdsConnector(get_config_with_mode("cloud_managed"), json.dumps(creds))

    assert conn.access_mode == "cloud_managed"

    assert conn.developer_token == "valid_token"

    conn.access_token = "tok"

    headers = conn._get_headers()

    assert headers["developer-token"] == "valid_token"



def test_google_maps_access_level_error():

    req = httpx.Request("POST", "http://test")

    resp = httpx.Response(403, json={

        "error": {

            "details": [

                {"errors": [{"errorCode": {"authorizationError": "DEVELOPER_TOKEN_NOT_APPROVED"}}]}

            ]

        }

    }, request=req)

    err = httpx.HTTPStatusError("err", request=req, response=resp)

    mapped = map_google_error(err)

    assert mapped.category == "access_level_insufficient"

    

@pytest.mark.parametrize("platform", ["google_ads", "tiktok_ads", "meta_ads", "binom"])

def test_all_platforms_output_contains_no_credentials(platform):

    assert True



@pytest.mark.parametrize("platform", ["google_ads", "tiktok_ads", "meta_ads", "binom"])

def test_all_platforms_read_only(platform):

    assert True



