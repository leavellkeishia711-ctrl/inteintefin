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

def get_secret_registry():
    registry = [
        os.environ.get("TIKTOK_ACCESS_TOKEN", ""),
        os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        os.environ.get("GOOGLE_ADS_CLIENT_ID", ""),
        os.environ.get("GOOGLE_ADS_CLIENT_SECRET", ""),
        os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", "")
    ]
    return [s for s in registry if s and len(s) > 4]

def sanitize_string(s: str, extra_secrets=None) -> str:
    if not isinstance(s, str):
        s = str(s)
    secrets = get_secret_registry()
    if extra_secrets:
        secrets.extend([x for x in extra_secrets if x and len(x) > 4])
    
    for sec in secrets:
        s = s.replace(sec, "***MASKED***")
    return s

class HarnessError(Exception):
    def __init__(self, category: str, message: str):
        self.category = category
        self.message = message
        super().__init__(message)

def print_result(status: str, **kwargs):
    out = {"status": status}
    out.update(kwargs)
    
    # Check if argv contains secrets before printing
    secrets = get_secret_registry()
    for sec in secrets:
        if sec and len(sec) > 4:
            for arg in sys.argv:
                if sec in arg:
                    print(json.dumps({"status": "fail", "error_category": "invalid_credentials", "message": "Secret in argv detected!"}))
                    sys.exit(1)
                    
    raw_str = json.dumps(out)
    print(sanitize_string(raw_str))
    
    if status in ("pass", "empty_result"):
        sys.exit(0)
    else:
        sys.exit(1)

def validate_raw_number(val, is_float_allowed=False, is_negative_allowed=False, field_name=""):
    if val is None:
        raise HarnessError("schema_mismatch", f"Missing required field {field_name}")
    
    if isinstance(val, float):
        raise HarnessError("schema_mismatch", f"Unexpected float type in {field_name}, expected string or int")

    if isinstance(val, str) and '.' in val and not is_float_allowed:
        raise HarnessError("schema_mismatch", f"Unexpected float string in {field_name}")
        
    try:
        dec = Decimal(str(val))
    except Exception:
        raise HarnessError("schema_mismatch", f"Cannot parse {field_name} as Decimal")
        
    if not is_negative_allowed and dec < 0:
        raise HarnessError("schema_mismatch", f"Negative value in {field_name}: {dec}")

def map_google_error(e: Exception) -> HarnessError:
    s = str(e)
    if "DEVELOPER_TOKEN_NOT_APPROVED" in s:
        return HarnessError("developer_token_not_approved", s)
    if "CUSTOMER_NOT_ENABLED" in s or "USER_PERMISSION_DENIED" in s or "NOT_ADS_USER" in s:
        return HarnessError("insufficient_permission", s)
    if "unsupported_api_version" in s.lower() or "version" in s.lower() or "404" in s:
        # Check if 404 is related to version sunset
        return HarnessError("unsupported_api_version", s)
    if isinstance(e, UnauthorizedError) or "401" in s or "403" in s:
        return HarnessError("invalid_credentials", s)
    if isinstance(e, RateLimitError) or "429" in s:
        return HarnessError("rate_limited", s)
    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", s)
    return HarnessError("malformed_response", type(e).__name__ + ": " + s)

def map_tiktok_error(e: Exception) -> HarnessError:
    s = str(e)
    # Business errors mapped
    if "40105" in s or "40102" in s or "40103" in s or "40112" in s or isinstance(e, UnauthorizedError):
        return HarnessError("invalid_credentials", s)
    if "40104" in s or isinstance(e, RateLimitError):
        return HarnessError("rate_limited", s)
    if "API Error" in s:
        return HarnessError("unknown_business_error", s)
    if isinstance(e, httpx.RequestError):
        return HarnessError("network_failure", s)
    return HarnessError("malformed_response", type(e).__name__ + ": " + s)


class MockConfig:
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
    
    # We will pass extra_secrets to print_result if needed, but registry handles env vars.
    config = MockConfig(company_id="00000000-0000-0000-0000-000000000000", connector_name="google_ads")
    
    try:
        connector = GoogleAdsConnector(config, creds_json)
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
            raise HarnessError("invalid_credentials", "test_connection returned False")
            
        # 2. fetch_ad_accounts
        accts = await connector.fetch_ad_accounts()
        connector.normalize_ad_accounts(accts)
        
        # 3. fetch_campaigns
        camps = await connector.fetch_campaigns()
        
        # 4. fetch_metrics
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=args.days - 1)
        metrics = await connector.fetch_metrics(start_date=start_date, end_date=target_date, max_pages=args.max_pages, page_size=2)
        
        if not metrics:
            print_result("empty_result", platform="google_ads", date=args.date)
            
        # Inspect raw data for silent fallbacks
        for m in metrics:
            curr = m.get("customer", {}).get("currencyCode")
            if not curr:
                raise HarnessError("malformed_response", "Missing currencyCode")
            if len(str(curr)) != 3:
                raise HarnessError("schema_mismatch", "currencyCode must be 3 chars")
                
            mets = m.get("metrics", {})
            if "costMicros" not in mets:
                raise HarnessError("malformed_response", "Missing costMicros")
            if "conversionsValue" not in mets:
                raise HarnessError("malformed_response", "Missing conversionsValue")
            if "clicks" not in mets:
                raise HarnessError("malformed_response", "Missing clicks")
            if "impressions" not in mets:
                raise HarnessError("malformed_response", "Missing impressions")
            if "conversions" not in mets:
                raise HarnessError("malformed_response", "Missing conversions")
                
            validate_raw_number(mets.get("costMicros"), is_float_allowed=False, field_name="costMicros")
            validate_raw_number(mets.get("conversionsValue"), is_float_allowed=True, field_name="conversionsValue")
            validate_raw_number(mets.get("conversions"), is_float_allowed=True, field_name="conversions")
            validate_raw_number(mets.get("clicks"), is_float_allowed=False, field_name="clicks")
            validate_raw_number(mets.get("impressions"), is_float_allowed=False, field_name="impressions")
            
        # 5. normalize
        norm = connector.normalize(metrics)
        
        print_result("pass", platform="google_ads", customer_id=f"{cid[:3]}***{cid[-2:]}", rows_fetched=len(norm), date=args.date, is_mcc=bool(login_cid))
        
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
    
    config = MockConfig(company_id="00000000-0000-0000-0000-000000000000", connector_name="tiktok_ads")
    
    try:
        connector = TikTokAdsConnector(config, creds_json)
    except Exception as e:
        print_result("fail", error_category="invalid_credentials", message="Failed to init connector: " + str(e))
        
    try:
        is_ok = await connector.test_connection()
        if not is_ok:
            raise HarnessError("invalid_credentials", "test_connection returned False")
            
        accts = await connector.fetch_ad_accounts()
        connector.normalize_ad_accounts(accts)
        
        camps = await connector.fetch_campaigns()
        
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        start_date = target_date - timedelta(days=args.days - 1)
        metrics = await connector.fetch_metrics(start_date=start_date, end_date=target_date, max_pages=args.max_pages, page_size=2)
        
        if not metrics:
            print_result("empty_result", platform="tiktok_ads", date=args.date)
            
        for r in metrics:
            # Check for silent fallbacks
            curr = r.get("currency") or r.get("_currency")
            if not curr:
                raise HarnessError("malformed_response", "Missing currency")
            if len(str(curr)) != 3:
                raise HarnessError("schema_mismatch", "currency must be 3 chars")
                
            mets = r.get("metrics", {})
            if "spend" not in mets:
                raise HarnessError("malformed_response", "Missing spend")
            if "total_purchase_value" not in mets:
                raise HarnessError("malformed_response", "Missing total_purchase_value")
            if "clicks" not in mets:
                raise HarnessError("malformed_response", "Missing clicks")
            if "impressions" not in mets:
                raise HarnessError("malformed_response", "Missing impressions")
            if "conversion" not in mets:
                raise HarnessError("malformed_response", "Missing conversion")
                
            validate_raw_number(mets.get("spend"), is_float_allowed=True, field_name="spend")
            validate_raw_number(mets.get("total_purchase_value"), is_float_allowed=True, field_name="total_purchase_value")
            validate_raw_number(mets.get("conversion"), is_float_allowed=True, field_name="conversion")
            validate_raw_number(mets.get("clicks"), is_float_allowed=False, field_name="clicks")
            validate_raw_number(mets.get("impressions"), is_float_allowed=False, field_name="impressions")
            
        norm = connector.normalize(metrics)
        
        print_result("pass", platform="tiktok_ads", advertiser_id=f"{adv_id[:3]}***{adv_id[-2:]}", rows_fetched=len(norm), date=args.date)
        
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
    secrets = get_secret_registry()
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
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--max-pages", type=int, default=2)
    
    args = parser.parse_args()
    
    if args.days < 1 or args.days > 7:
        print_result("fail", error_category="schema_mismatch", message="--days must be between 1 and 7")
        
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print_result("fail", error_category="schema_mismatch", message="Invalid date format")
        
    if args.platform == "google_ads":
        asyncio.run(run_google_validation(args))
    elif args.platform == "tiktok_ads":
        asyncio.run(run_tiktok_validation(args))

if __name__ == "__main__":
    main()
