import os
import sys
import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
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

def print_result(status: str, **kwargs):
    out = {"status": status}
    if status == "empty_result":
        out["schema_validated"] = False
    elif status == "pass":
        out["schema_validated"] = True
    out.update(kwargs)

    # Check if argv contains secrets before printing
    secrets = registry._secrets
    for sec in secrets:
        if sec and len(sec) > 4:
            for arg in sys.argv:
                if sec in arg:
                    print(json.dumps({"status": "fail", "error_category": "invalid_credentials", "message": "Secret in argv detected!"}))
                    sys.exit(1)

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
    s = str(e)
    if isinstance(e, ConnectorError):
        code = getattr(e, "api_error_code", None)
        status = getattr(e, "status_code", None)

        if code == "DEVELOPER_TOKEN_NOT_APPROVED":
            return HarnessError("developer_token_not_approved", s)
        if code in ("CUSTOMER_NOT_ENABLED", "USER_PERMISSION_DENIED", "NOT_ADS_USER"):
            return HarnessError("insufficient_permission", s)

        if status == 404:
            return HarnessError("unsupported_api_version", s)

        if isinstance(e, UnauthorizedError) or status in (401, 403):
            return HarnessError("invalid_credentials", s)
        if isinstance(e, RateLimitError) or status == 429:
            return HarnessError("rate_limited", s)

    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", s)

    return HarnessError("malformed_response", type(e).__name__ + ": " + s)

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

        # 5. normalize and exhaustive check
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
        connector.normalize_ad_accounts(accts)

        camps = await connector.fetch_campaigns()
        for c in camps:
            if "campaign_id" not in c:
                raise HarnessError("malformed_response", "TikTok campaign missing campaign_id")

        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=args.days - 1)
        metrics = await connector.fetch_metrics(start_date=start_date, end_date=target_date, max_pages=args.max_pages, page_size=args.page_size)

        if not metrics:
            print_result("empty_result", platform="tiktok_ads", date=args.date)

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

        print_result("pass", platform="tiktok_ads", advertiser_id=f"{adv_id[:3]}***{adv_id[-2:]}", rows_fetched=len(norm), date=args.date, pages_fetched=getattr(connector, "last_pages_fetched", 1), saw_next_page=getattr(connector, "last_saw_next_page", False), page_size_used=args.page_size)

    except HarnessError as e:
        print_result("fail", platform="tiktok_ads", error_category=e.category, message=e.message)
    except Exception as e:
        he = map_tiktok_error(e)
        print_result("fail", platform="tiktok_ads", error_category=he.category, message=he.message)

def main():
    if os.environ.get("LIVE_CONNECTOR_VALIDATION") != "1":
        sys.stderr.write("Error: LIVE_CONNECTOR_VALIDATION=1 environment variable is required to run this script.\n")
        sys.exit(1)

    # Check argv for secrets
    secrets = registry._secrets
    for sec in secrets:
        if sec and len(sec) > 4:
            for arg in sys.argv:
                if sec in arg:
                    sys.stderr.write("Secret detected in argv!\n")
                    sys.exit(1)

    parser = argparse.ArgumentParser(description="Live Connector Validation")
    parser.add_argument("--platform", choices=["google_ads", "tiktok_ads"], required=True)
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
    except Exception as e:
        print_result("fail", error_category="internal_error", message=str(e))

if __name__ == "__main__":
    main()

