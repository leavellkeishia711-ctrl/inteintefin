import os
import sys
import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal, InvalidOperation, InvalidOperation
import httpx

# Ensure python path allows importing from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.connectors.base import UnauthorizedError, RateLimitError, ConnectorError, NormalizedRecord
from app.connectors.google_ads import GoogleAdsConnector
from app.connectors.tiktok_ads import TikTokAdsConnector

class SecretRegistry:
    def __init__(self):
        self._secrets = set()
        self.register(os.environ.get("TIKTOK_ACCESS_TOKEN", ""))
        self.register(os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""))
        self.register(os.environ.get("GOOGLE_ADS_CLIENT_ID", ""))
        self.register(os.environ.get("GOOGLE_ADS_CLIENT_SECRET", ""))
        self.register(os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", ""))

    def register(self, secret: str):
        if secret and isinstance(secret, str) and len(secret) > 0:
            self._secrets.add(secret)

    def sanitize(self, s: str) -> str:
        if not isinstance(s, str):
            s = str(s)
        for sec in self._secrets:
            s = s.replace(sec, "***MASKED***")
        return s

registry = SecretRegistry()

def sanitize_string(s: str) -> str:
    return registry.sanitize(s)

class HarnessError(Exception):
    def __init__(self, category: str, message: str):
        self.category = category
        self.message = message
        super().__init__(message)

def assert_no_secrets_in_argv(argv, registry):
    secrets = registry._secrets
    for sec in secrets:
        if sec:
            for arg in argv:
                if sec in arg:
                    print(json.dumps({"status": "fail", "error_category": "invalid_credentials", "message": "Secret in argv detected!"}))
                    sys.exit(1)

def print_result(status: str, **kwargs):
    out = {"status": status}
    if status == "empty_result":
        out["schema_validated"] = False
    elif status == "pass":
        out["schema_validated"] = True
    out.update(kwargs)

    # Check if argv contains secrets before printing
    assert_no_secrets_in_argv(sys.argv, registry)

    raw_str = json.dumps(out)
    print(sanitize_string(raw_str))

    if status == "pass":
        sys.exit(0)
    elif status == "empty_result":
        if "--allow-empty" in sys.argv:
            sys.exit(0)
        else:
            sys.exit(2)
    else:
        sys.exit(1)

def validate_field(val, expected="int_string", is_negative_allowed=False, field_name=""):
    if val is None:
        raise HarnessError("schema_mismatch", f"Missing required field {field_name}")

    if expected == "int_string":
        if isinstance(val, float):
            raise HarnessError("schema_mismatch", f"Unexpected float type in {field_name}, expected int_string")
        if isinstance(val, str) and '.' in val:
            raise HarnessError("schema_mismatch", f"Unexpected float string in {field_name}, expected int_string")
    elif expected == "decimal_string":
        if isinstance(val, float):
            raise HarnessError("schema_mismatch", f"Unexpected float type in {field_name}, expected decimal_string")
        # float string or int string is OK
    elif expected == "decimal_number":
        # float type, int type, or string is OK
        pass

    try:
        dec = Decimal(repr(val)) if isinstance(val, float) else Decimal(str(val))
    except Exception:
        raise HarnessError("schema_mismatch", f"Cannot parse {field_name} as Decimal")

    if not is_negative_allowed and dec < 0:
        raise HarnessError("schema_mismatch", f"Negative value in {field_name}: {dec}")

def map_google_error(e: Exception) -> HarnessError:
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        try:
            body = e.response.json()
            errs = body.get("error", {}).get("details", [])
            for d in errs:
                if "errors" in d:
                    for inner in d["errors"]:
                        err_code = inner.get("errorCode", {})
                        if "authenticationError" in err_code:
                            if err_code["authenticationError"] == "CUSTOMER_NOT_FOUND":
                                return HarnessError("customer_not_found", "Customer not found")
                            return HarnessError("invalid_credentials", f"Google auth error: {err_code}")
                        if "authorizationError" in err_code:
                            if err_code["authorizationError"] == "USER_PERMISSION_DENIED":
                                return HarnessError("insufficient_permission", "User permission denied")
                            if err_code["authorizationError"] == "DEVELOPER_TOKEN_NOT_APPROVED":
                                return HarnessError("access_level_insufficient", "Cloud project without required access level")
                            if err_code["authorizationError"] == "CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION":
                                return HarnessError("access_level_insufficient", "Cloud project not approved for production")
                            if err_code["authorizationError"] == "ACTION_NOT_PERMITTED":
                                return HarnessError("access_level_insufficient", "Action not permitted (insufficient access level)")
                            if err_code["authorizationError"] == "CUSTOMER_NOT_ENABLED":
                                return HarnessError("login_customer_mismatch", "Customer not enabled / mismatch")
                            return HarnessError("insufficient_permission", f"Google authz error: {err_code}")
                        if "quotaError" in err_code:
                            return HarnessError("rate_limit", f"Google quota error: {err_code}")
                        if "requestError" in err_code and err_code["requestError"] == "UNSUPPORTED_VERSION":
                            return HarnessError("unsupported_api_version", "Unsupported API version")
            
            msg = body.get("error", {}).get("message", "").lower()
            if "authentication" in msg or "invalid token" in msg:
                return HarnessError("invalid_credentials", msg)
            if "unsupported" in msg and "version" in msg:
                return HarnessError("unsupported_api_version", msg)
        except Exception:
            pass
        return HarnessError("network_failure", f"HTTP {status}")
    if e.__class__.__name__ == "ConnectorError":
        api_code = getattr(e, "api_error_code", "")
        msg = str(e).lower()
        if api_code == "DEVELOPER_TOKEN_NOT_APPROVED" or "developer_token_not_approved" in msg:
            return HarnessError("developer_token_not_approved", "Developer token not approved")
        if getattr(e, "status_code", None) == 404 or "unsupported_api_version" in msg:
            return HarnessError("unsupported_api_version", "Unsupported API version")
    return HarnessError("network_failure", str(e))

def map_tiktok_error(e: Exception) -> HarnessError:
    s = str(e)
    if isinstance(e, ConnectorError):
        code = getattr(e, "api_error_code", None)
        status = getattr(e, "status_code", None)

        if isinstance(e, UnauthorizedError) or status in (401, 403) or str(code) in ("40105", "40102", "40103", "40112"):
            return HarnessError("invalid_credentials", s)
        if isinstance(e, RateLimitError) or status == 429 or str(code) == "40104":
            return HarnessError("rate_limited", s)

        if code and code != "None":
            return HarnessError("unknown_business_error", s)

    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", s)
    return HarnessError("malformed_response", type(e).__name__ + ": " + s)


class HarnessConnectorConfig:
    def __init__(self, company_id, connector_name):
        self.company_id = company_id
        self.connector_name = connector_name


async def run_google_validation(args):
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    client_id = os.environ.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN")

    cid = args.customer_id or os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
    login_cid = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")

    if not all([dev_token, client_id, client_secret, refresh_token, cid]):
        print_result("fail", error_category="invalid_credentials", message="Missing Google Ads environment variables or customer_id")

    creds_dict = {
        "developer_token": dev_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "customer_id": cid,
    }
    if login_cid:
        creds_dict["login_customer_id"] = login_cid

    creds_json = json.dumps(creds_dict)
    registry.register(creds_json)
    for k, v in creds_dict.items():
        if isinstance(v, str):
            registry.register(v)

    config = HarnessConnectorConfig(company_id="00000000-0000-0000-0000-000000000000", connector_name="google_ads")

    try:
        connector = GoogleAdsConnector(config, creds_json, timeout=args.timeout)
        connector.register_secret = registry.register
    except Exception as e:
        print_result("fail", error_category="invalid_credentials", message="Failed to init connector: " + str(e))

    # Hack to allow overriding API version for testing
    if getattr(args, 'api_version', None):
        import app.connectors.google_ads as ga_mod
        ga_mod.GOOGLE_ADS_API_VERSION = args.api_version

    try:
        # 1. test_connection
        is_ok = await connector.test_connection()
        if not is_ok:
            # Re-trigger explicitly to catch the precise exception
            await connector.fetch_ad_accounts()
            raise HarnessError("invalid_credentials", "test_connection returned False but no specific exception was raised")

        # 2. fetch_ad_accounts
        accts = await connector.fetch_ad_accounts()
        for a in accts:
            if "customer" not in a or "id" not in a["customer"] or "currencyCode" not in a["customer"]:
                raise HarnessError("malformed_response", "Google account missing id or currencyCode")
            if str(a["customer"]["id"]) != str(connector.customer_id):
                raise HarnessError("schema_mismatch", "Account response customer.id does not match requested")
        connector.normalize_ad_accounts(accts)

        # 3. fetch_campaigns
        camps = await connector.fetch_campaigns()
        for c in camps:
            if "campaign" not in c or "id" not in c["campaign"]:
                raise HarnessError("malformed_response", "Google campaign missing campaign.id")
            if "customer" in c and str(c["customer"].get("id")) != str(connector.customer_id):
                raise HarnessError("schema_mismatch", "Campaign response customer.id does not match requested")

        # 4. fetch_metrics
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=args.days - 1)
        metrics = await connector.fetch_metrics(start_date=start_date, end_date=target_date, max_pages=args.max_pages, page_size=args.page_size)

        if not metrics:
            print_result("empty_result", platform="google_ads", date=args.date)



        # 5. raw harness validation before normalize
        for m in metrics:
            mets = m.get("metrics", {})
            
            # Google Contract:
            # costMicros: int_string
            # clicks: int_string
            # impressions: int_string
            # conversions: decimal_number
            # conversionsValue: decimal_number
            
            validate_field(mets.get("costMicros"), expected="int_string", field_name="costMicros")
            validate_field(mets.get("clicks"), expected="int_string", field_name="clicks")
            validate_field(mets.get("impressions"), expected="int_string", field_name="impressions")
            validate_field(mets.get("conversions"), expected="decimal_number", field_name="conversions")
            validate_field(mets.get("conversionsValue"), expected="decimal_number", field_name="conversionsValue")
            
            if "customer" in m and "id" in m["customer"] and str(m["customer"]["id"]) != str(connector.customer_id):
                raise HarnessError("schema_mismatch", "Google metrics row customer.id does not match requested")
            if "campaign" not in m or "id" not in m["campaign"] or not m["campaign"]["id"]:
                raise HarnessError("malformed_response", "Google metrics row missing campaign.id")

        norm = connector.normalize(metrics)
        if len(norm) != len(metrics):
            raise HarnessError("schema_mismatch", f"Normalization length mismatch: {len(metrics)} vs {len(norm)}")

        for m, r in zip(metrics, norm):
            if not r.external_id:
                raise HarnessError("schema_mismatch", "Normalized record missing external_id")
            if not (start_date <= r.stat_date <= target_date):
                raise HarnessError("schema_mismatch", f"stat_date {r.stat_date} out of bounds")
            if not r.currency or len(r.currency) != 3:
                raise HarnessError("schema_mismatch", f"Normalized currency invalid: {r.currency}")
            if not isinstance(r.spend, Decimal) or not isinstance(r.revenue, Decimal) or not isinstance(r.conversions, Decimal):
                raise HarnessError("schema_mismatch", "Normalized money/conversions fields are not Decimal")
            if not isinstance(r.clicks, int) or not isinstance(r.impressions, int):
                raise HarnessError("schema_mismatch", "Normalized clicks/impressions are not int")

            mets = m.get("metrics", {})
            for field in ["costMicros", "conversionsValue", "conversions", "clicks", "impressions"]:
                if field not in mets:
                    raise HarnessError("malformed_response", f"Missing field in Google metrics: {field}")

            raw_cost = Decimal(str(mets["costMicros"]))
            if raw_cost != r.spend * 1000000:
                raise HarnessError("schema_mismatch", f"spend {r.spend} does not match costMicros {raw_cost}")

            raw_rev = Decimal(str(mets["conversionsValue"]))
            if raw_rev != r.revenue:
                raise HarnessError("schema_mismatch", f"revenue {r.revenue} does not match conversionsValue {raw_rev}")

            raw_conv = Decimal(str(mets["conversions"]))
            if raw_conv != r.conversions:
                raise HarnessError("schema_mismatch", f"conversions {r.conversions} does not match {raw_conv}")

            if int(str(mets["clicks"])) != r.clicks:
                raise HarnessError("schema_mismatch", "clicks mismatch")
            if int(str(mets["impressions"])) != r.impressions:
                raise HarnessError("schema_mismatch", "impressions mismatch")
            
            cust_id = m.get("customer", {}).get("id")
            if cust_id and str(cust_id) != str(connector.customer_id):
                raise HarnessError("schema_mismatch", "Metrics response customer.id does not match requested")
            if not m.get("campaign", {}).get("id"):
                raise HarnessError("malformed_response", "Campaign metrics missing campaign.id")

        print_result("pass", platform="google_ads", customer_id=f"{cid[:3]}***{cid[-2:]}", rows_fetched=len(norm), date=args.date, is_mcc=bool(login_cid), pages_fetched=getattr(connector, "last_pages_fetched", 1), saw_next_page=getattr(connector, "last_saw_next_page", False), page_size_used=args.page_size)

    except HarnessError as e:
        print_result("fail", platform="google_ads", error_category=e.category, message=e.message)
    except Exception as e:
        he = map_google_error(e)
        print_result("fail", platform="google_ads", error_category=he.category, message=he.message)


async def run_tiktok_validation(args):
    token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    adv_id = args.advertiser_id or os.environ.get("TIKTOK_ADVERTISER_ID")

    if not token or not adv_id:
        print_result("fail", error_category="invalid_credentials", message="Missing TIKTOK_ACCESS_TOKEN or advertiser_id")

    creds_dict = {
        "access_token": token,
        "advertiser_id": adv_id,
    }
    creds_json = json.dumps(creds_dict)
    registry.register(creds_json)
    for k, v in creds_dict.items():
        if isinstance(v, str):
            registry.register(v)

    config = HarnessConnectorConfig(company_id="00000000-0000-0000-0000-000000000000", connector_name="tiktok_ads")

    try:
        connector = TikTokAdsConnector(config, creds_json, timeout=args.timeout)
        connector.register_secret = registry.register
    except Exception as e:
        print_result("fail", error_category="invalid_credentials", message="Failed to init connector: " + str(e))

    try:
        is_ok = await connector.test_connection()
        if not is_ok:
            await connector.fetch_ad_accounts()
            raise HarnessError("invalid_credentials", "test_connection returned False but no specific exception was raised")

        accts = await connector.fetch_ad_accounts()
        for a in accts:
            if "advertiser_id" not in a or "currency" not in a:
                raise HarnessError("malformed_response", "TikTok account missing advertiser_id or currency")
            if str(a.get("advertiser_id")) != connector.advertiser_id:
                raise HarnessError("schema_mismatch", "TikTok account advertiser_id mismatch")
        connector.normalize_ad_accounts(accts)

        camps = await connector.fetch_campaigns()
        for c in camps:
            if not c.get("campaign_id"):
                raise HarnessError("malformed_response", "TikTok campaign missing campaign_id")
            if "advertiser_id" in c and str(c.get("advertiser_id")) != connector.advertiser_id:
                raise HarnessError("schema_mismatch", "TikTok campaign advertiser_id mismatch")

        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=args.days - 1)
        metrics = await connector.fetch_metrics(start_date=start_date, end_date=target_date, max_pages=args.max_pages, page_size=args.page_size)

        if not metrics:
            print_result("empty_result", platform="tiktok_ads", date=args.date)



        # raw harness validation before normalize
        for m in metrics:
            dim = m.get("dimensions", {})
            if not dim.get("campaign_id"):
                raise HarnessError("malformed_response", "TikTok row missing campaign_id")
            if "stat_time_day" not in dim:
                raise HarnessError("malformed_response", "TikTok row missing stat_time_day")
            if "advertiser_id" in dim and str(dim["advertiser_id"]) != connector.advertiser_id:
                raise HarnessError("schema_mismatch", "TikTok row advertiser_id mismatch")
            if "advertiser_id" in m and str(m["advertiser_id"]) != connector.advertiser_id:
                raise HarnessError("schema_mismatch", "TikTok row advertiser_id mismatch")
                
            mets = m.get("metrics", {})
            
            # TikTok Contract:
            # spend: decimal_string
            # total_purchase_value: decimal_string
            # conversion: decimal_string
            # clicks: int_string
            # impressions: int_string
            validate_field(mets.get("spend"), expected="decimal_string", field_name="spend")
            validate_field(mets.get("total_purchase_value"), expected="decimal_string", field_name="total_purchase_value")
            validate_field(mets.get("conversion"), expected="decimal_string", field_name="conversion")
            validate_field(mets.get("clicks"), expected="int_string", field_name="clicks")
            validate_field(mets.get("impressions"), expected="int_string", field_name="impressions")

        norm = connector.normalize(metrics)
        if len(norm) != len(metrics):
            raise HarnessError("schema_mismatch", f"Normalization length mismatch: {len(metrics)} vs {len(norm)}")

        for m, r in zip(metrics, norm):
            if not r.external_id:
                raise HarnessError("schema_mismatch", "Normalized record missing external_id")
            if not (start_date <= r.stat_date <= target_date):
                raise HarnessError("schema_mismatch", f"stat_date {r.stat_date} out of bounds")
            if not r.currency or len(r.currency) != 3:
                raise HarnessError("schema_mismatch", f"Normalized currency invalid: {r.currency}")
            if not isinstance(r.spend, Decimal) or not isinstance(r.revenue, Decimal) or not isinstance(r.conversions, Decimal):
                raise HarnessError("schema_mismatch", "Normalized money/conversions fields are not Decimal")
            if not isinstance(r.clicks, int) or not isinstance(r.impressions, int):
                raise HarnessError("schema_mismatch", "Normalized clicks/impressions are not int")

            mets = m.get("metrics", {})
            for field in ["spend", "total_purchase_value", "conversion", "clicks", "impressions"]:
                if field not in mets:
                    raise HarnessError("malformed_response", f"Missing field in TikTok metrics: {field}")

            raw_spend = Decimal(str(mets["spend"]).replace(',', ''))
            if raw_spend != r.spend:
                raise HarnessError("schema_mismatch", f"spend {r.spend} does not match {raw_spend}")

            raw_rev = Decimal(str(mets["total_purchase_value"]).replace(',', ''))
            if raw_rev != r.revenue:
                raise HarnessError("schema_mismatch", f"revenue {r.revenue} does not match {raw_rev}")

            raw_conv = Decimal(str(mets["conversion"]).replace(',', ''))
            if raw_conv != r.conversions:
                raise HarnessError("schema_mismatch", f"conversions {r.conversions} does not match {raw_conv}")

            if int(str(mets["clicks"]).replace(',', '')) != r.clicks:
                raise HarnessError("schema_mismatch", "clicks mismatch")
            if int(str(mets["impressions"]).replace(',', '')) != r.impressions:
                raise HarnessError("schema_mismatch", "impressions mismatch")
                
            dimensions = m.get("dimensions", {})
            if not dimensions.get("campaign_id") or not dimensions.get("stat_time_day"):
                raise HarnessError("malformed_response", "TikTok report missing campaign_id or stat_time_day")
            if "advertiser_id" in m and str(m.get("advertiser_id")) != connector.advertiser_id:
                raise HarnessError("schema_mismatch", "TikTok report advertiser_id mismatch")

        print_result("pass", platform="tiktok_ads", advertiser_id=f"{adv_id[:3]}***{adv_id[-2:]}", rows_fetched=len(norm), date=args.date, pages_fetched=getattr(connector, "last_pages_fetched", 1), saw_next_page=getattr(connector, "last_saw_next_page", False), page_size_used=args.page_size)

    except HarnessError as e:
        print_result("fail", platform="tiktok_ads", error_category=e.category, message=e.message)
    except Exception as e:
        he = map_tiktok_error(e)
        print_result("fail", platform="tiktok_ads", error_category=he.category, message=he.message)


def map_meta_error(e: Exception) -> HarnessError:
    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", f"Network error: {type(e).__name__}")
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        try:
            body = e.response.json()
            err = body.get("error", {})
            code = err.get("code")
            subcode = err.get("error_subcode")
            
            if code == 190:
                return HarnessError("invalid_credentials", "Meta invalid/expired token")
            if code in (200, 10, 294):
                return HarnessError("insufficient_permission", "Meta insufficient permission")
            if code in (4, 17, 32, 613, 80004):
                return HarnessError("rate_limit", "Meta rate limit exceeded")
            if code == 100:
                return HarnessError("malformed_request", "Meta malformed request")
            if code == 2635 or "unsupported" in str(err.get("message", "")).lower():
                return HarnessError("unsupported_api_version", "Meta unsupported API version")
        except Exception:
            pass
        return HarnessError("network_failure", f"Meta HTTP status {status}")
    return HarnessError("network_failure", str(e))

async def run_meta_validation(args):
    from app.connectors.meta_ads import MetaAdsConnector
    import os
    token = os.environ.get("META_ACCESS_TOKEN")
    adv_id = os.environ.get("META_AD_ACCOUNT_ID")
    api_version = os.environ.get("META_API_VERSION", "v26.0")
    if not token or not adv_id:
        print_result("fail", error_category="config_error", message="Missing Meta credentials")
        return

    # Normalize ad account id
    if not adv_id.startswith("act_"):
        adv_id = "act_" + adv_id

    try:
        class DummyConfig:
            connector_name = "meta_ads"
            company_id = 1
            settings = {"api_version": api_version, "currency": "USD"}
            
        connector = MetaAdsConnector(config=DummyConfig(), decrypted_api_key=token)

        # 1. Test permissions (me/permissions)
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get(f"https://graph.facebook.com/{api_version}/me/permissions", headers=headers)
            res.raise_for_status()
            perms = res.json().get("data", [])
            has_ads_read = any(p.get("permission") == "ads_read" and p.get("status") == "granted" for p in perms)
            if not has_ads_read:
                raise HarnessError("insufficient_permission", "Missing ads_read permission")

        # 2. Get ad account
        async with httpx.AsyncClient() as client:
            res = await client.get(f"https://graph.facebook.com/{api_version}/{adv_id}?fields=account_id,currency,account_status,timezone_name", headers=headers)
            res.raise_for_status()
            acct = res.json()
            currency = acct.get("currency", "USD")
            connector.config.settings["currency"] = currency

        # 3. List campaigns
        camps = await connector.fetch_campaigns()

        # 4. Fetch metrics
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=args.days - 1)
        
        metrics = await connector.fetch_metrics(start_date=start_date, end_date=target_date, max_pages=args.max_pages, page_size=args.page_size)

        if not metrics:
            print_result("empty_result", platform="meta_ads", date=args.date)
            return
            
        # raw harness validation before normalize
        for m in metrics:
            validate_field(m.get("spend"), expected="decimal_string", field_name="spend")
            validate_field(m.get("clicks"), expected="int_string", field_name="clicks")
            validate_field(m.get("impressions"), expected="int_string", field_name="impressions")

        norm = connector.normalize(metrics)
        if len(norm) != len(metrics):
            raise HarnessError("schema_mismatch", f"Normalization length mismatch: {len(metrics)} vs {len(norm)}")

        for r in norm:
            if not r.currency or len(r.currency) != 3:
                raise HarnessError("schema_mismatch", f"Normalized currency invalid: {r.currency}")

        print_result("pass", platform="meta_ads", advertiser_id=f"{adv_id[:4]}***{adv_id[-2:]}", rows_fetched=len(norm), date=args.date)

    except HarnessError as e:
        print_result("fail", platform="meta_ads", error_category=e.category, message=e.message)
    except Exception as e:
        he = map_meta_error(e)
        print_result("fail", platform="meta_ads", error_category=he.category, message=he.message)


def map_binom_error(e: Exception) -> HarnessError:
    import urllib.parse
    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", f"Network error: {type(e).__name__}")
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status in (401, 403):
            return HarnessError("invalid_credentials", "Binom invalid credentials / insufficient permission")
        if status == 404:
            return HarnessError("unsupported_api_version", f"Binom 404 on endpoint. URL path: {urllib.parse.urlparse(str(e.request.url)).path}")
        return HarnessError("network_failure", f"Binom HTTP status {status}")
    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", str(e))
    return HarnessError("network_failure", str(e))

async def run_binom_validation(args):
    from app.connectors.binom import BinomConnector
    import os
    base_url = os.environ.get("BINOM_BASE_URL")
    api_key = os.environ.get("BINOM_API_KEY")
    currency = os.environ.get("BINOM_CURRENCY", "USD")
    
    if not base_url or not api_key:
        print_result("fail", error_category="config_error", message="Missing Binom credentials")
        return

    try:
        class DummyConfig:
            connector_name = "binom"
            company_id = 1
            settings = {"base_url": base_url, "currency": currency}
            
        connector = BinomConnector(config=DummyConfig(), decrypted_api_key=api_key)

        conn_ok = await connector.test_connection()
        if not conn_ok:
            raise HarnessError("invalid_credentials", "Binom test_connection failed")

        camps = await connector.fetch_campaigns()
        
        if isinstance(camps, str) and "<html" in camps.lower():
            raise HarnessError("malformed_response", "Binom returned HTML instead of JSON. base URL probably wrong")

        metrics = await connector.fetch_metrics()
        
        if isinstance(metrics, str) and "<html" in metrics.lower():
            raise HarnessError("malformed_response", "Binom returned HTML instead of JSON. base URL probably wrong")

        if not metrics:
            print_result("empty_result", platform="binom", date=args.date)
            return

        norm = connector.normalize(metrics)

        print_result("pass", platform="binom", rows_fetched=len(norm), date=args.date)

    except HarnessError as e:
        print_result("fail", platform="binom", error_category=e.category, message=e.message)
    except Exception as e:
        he = map_binom_error(e)
        print_result("fail", platform="binom", error_category=he.category, message=he.message)

def main():
    try:
        from dotenv import load_dotenv
        load_dotenv('.env.local')
    except ImportError:
        pass
    if os.environ.get("LIVE_CONNECTOR_VALIDATION") != "1":
        sys.stderr.write("Error: LIVE_CONNECTOR_VALIDATION=1 environment variable is required to run this script.\n")
        sys.exit(1)

    # Check argv for secrets
    assert_no_secrets_in_argv(sys.argv, registry)

    parser = argparse.ArgumentParser(description="Live Connector Validation")
    parser.add_argument("--platform", choices=["google_ads", "tiktok_ads", "meta_ads", "binom"], required=True)
    parser.add_argument("--customer-id", help="Google Ads customer ID")
    parser.add_argument("--advertiser-id", help="TikTok Ads advertiser ID")
    parser.add_argument("--date", help="End date in YYYY-MM-DD", default=(datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d"))
    parser.add_argument("--days", type=int, default=1, help="Number of days to fetch")
    parser.add_argument("--api-version", help="Override Google Ads API version")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--allow-empty", action="store_true", help="Treat empty results as pass instead of inconclusive")

    args = parser.parse_args()

    if args.days < 1 or args.days > 7:
        print_result("fail", error_category="schema_mismatch", message="--days must be between 1 and 7")

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print_result("fail", error_category="schema_mismatch", message="Invalid date format")

    try:
        if args.platform == "google_ads":
            asyncio.run(run_google_validation(args))
        elif args.platform == "tiktok_ads":
            asyncio.run(run_tiktok_validation(args))
        elif args.platform == "meta_ads":
            asyncio.run(run_meta_validation(args))
        elif args.platform == "binom":
            asyncio.run(run_binom_validation(args))

    except Exception as e:
        sys.stderr.write(registry.mask_secrets(f"Unexpected internal error: {type(e).__name__} - {str(e)}\n"))
        import traceback
        sys.stderr.write(registry.mask_secrets(traceback.format_exc()))
        sys.exit(99)


if __name__ == "__main__":
    main()

