import os
import sys
import argparse
import asyncio
import httpx
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure python path allows importing from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.connectors.base import with_retry, UnauthorizedError, RateLimitError, ConnectorError

def sanitize_exception(e: Exception) -> str:
    err_str = str(e)
    # Generic obfuscation of potential secrets
    for token in [
        os.environ.get("TIKTOK_ACCESS_TOKEN", ""),
        os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
        os.environ.get("GOOGLE_ADS_CLIENT_ID", ""),
        os.environ.get("GOOGLE_ADS_CLIENT_SECRET", ""),
        os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", "")
    ]:
        if token and len(token) > 4:
            err_str = err_str.replace(token, "***MASKED***")
    return err_str

async def validate_google_ads(customer_id: str):
    dev_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
    client_id = os.environ.get("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN")
    login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    
    if not all([dev_token, client_id, client_secret, refresh_token, customer_id]):
        print(json.dumps({"status": "fail", "error": "Missing Google Ads environment variables or customer_id"}))
        sys.exit(1)
        
    try:
        # 1. OAuth
        async def fetch_token():
            async with httpx.AsyncClient() as client:
                res = await client.post("https://oauth2.googleapis.com/token", data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }, timeout=10)
                if res.status_code in (401, 403):
                    raise UnauthorizedError("OAuth Failed")
                res.raise_for_status()
                return res.json()["access_token"]
        
        access_token = await with_retry(fetch_token)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": dev_token,
            "Content-Type": "application/json"
        }
        if login_customer_id:
            headers["login-customer-id"] = str(login_customer_id).replace("-", "")
            
        c_id = str(customer_id).replace("-", "")
        
        # 2. Customer query
        async def fetch_customer():
            async with httpx.AsyncClient() as client:
                query = "SELECT customer.currency_code FROM customer LIMIT 1"
                res = await client.post(
                    f"https://googleads.googleapis.com/v16/customers/{c_id}/googleAds:search",
                    headers=headers,
                    json={"query": query},
                    timeout=15
                )
                if res.status_code in (401, 403):
                    raise UnauthorizedError("Customer Info Failed")
                res.raise_for_status()
                return res.json()
                
        cust_data = await with_retry(fetch_customer)
        currency = cust_data.get("results", [{}])[0].get("customer", {}).get("currencyCode", "USD")
        
        # 3. Metrics query
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        async def fetch_metrics():
            async with httpx.AsyncClient() as client:
                query = f"SELECT campaign.id, segments.date, metrics.cost_micros, metrics.conversions, metrics.clicks, metrics.impressions FROM campaign WHERE segments.date = '{target_date}' LIMIT 10"
                res = await client.post(
                    f"https://googleads.googleapis.com/v16/customers/{c_id}/googleAds:search",
                    headers=headers,
                    json={"query": query},
                    timeout=15
                )
                if res.status_code in (401, 403):
                    raise UnauthorizedError("Metrics Query Failed")
                res.raise_for_status()
                return res.json()
                
        metrics_data = await with_retry(fetch_metrics)
        rows = metrics_data.get("results", [])
        
        # Validation
        for r in rows:
            m = r.get("metrics", {})
            c_micros = int(m.get("costMicros", 0))
            if c_micros < 0:
                raise ValueError("Negative cost found")
            # validate decimal conversion
            Decimal(str(m.get("conversions", "0")))
            
        print(json.dumps({
            "platform": "google_ads",
            "customer_id": f"{c_id[:3]}***{c_id[-2:]}",
            "currency": currency,
            "date_range": target_date,
            "rows_fetched": len(rows),
            "status": "pass"
        }))
        
    except Exception as e:
        safe_msg = sanitize_exception(e)
        print(json.dumps({"platform": "google_ads", "status": "fail", "error": type(e).__name__, "message": safe_msg}))
        sys.exit(1)


async def validate_tiktok_ads(advertiser_id: str):
    access_token = os.environ.get("TIKTOK_ACCESS_TOKEN")
    if not access_token or not advertiser_id:
        print(json.dumps({"status": "fail", "error": "Missing TIKTOK_ACCESS_TOKEN or advertiser_id"}))
        sys.exit(1)
        
    try:
        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        # 1. Advertiser info
        async def fetch_advertiser():
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/",
                    headers=headers,
                    params={"advertiser_ids": f'["{advertiser_id}"]'},
                    timeout=15
                )
                if res.status_code in (401, 403):
                    raise UnauthorizedError("Advertiser Info Failed")
                res.raise_for_status()
                data = res.json()
                if data.get("code") != 0:
                    raise Exception(f'TikTok API Error {data.get("code")}: {data.get("message")}')
                return data

        adv_data = await with_retry(fetch_advertiser)
        currency = adv_data.get("data", {}).get("list", [{}])[0].get("currency", "USD")
        
        # 2. Report
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        async def fetch_report():
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",
                    headers=headers,
                    params={
                        "advertiser_id": advertiser_id,
                        "report_type": "BASIC",
                        "data_level": "AUCTION_CAMPAIGN",
                        "dimensions": '["campaign_id","stat_time_day"]',
                        "metrics": '["spend","clicks","impressions","conversion","total_purchase_value"]',
                        "start_date": target_date,
                        "end_date": target_date,
                        "page_size": 10
                    },
                    timeout=15
                )
                if res.status_code in (401, 403):
                    raise UnauthorizedError("Report Query Failed")
                res.raise_for_status()
                data = res.json()
                if data.get("code") != 0:
                    raise Exception(f'TikTok API Error {data.get("code")}: {data.get("message")}')
                return data
                
        report_data = await with_retry(fetch_report)
        rows = report_data.get("data", {}).get("list", [])
        
        for r in rows:
            m = r.get("metrics", {})
            spend = Decimal(str(m.get("spend", "0")))
            if spend < 0:
                raise ValueError("Negative spend found")
            int(m.get("clicks", 0))
            int(m.get("impressions", 0))
            Decimal(str(m.get("conversion", "0")))
            
        print(json.dumps({
            "platform": "tiktok_ads",
            "advertiser_id": f"{advertiser_id[:3]}***{advertiser_id[-2:]}",
            "currency": currency,
            "date_range": target_date,
            "rows_fetched": len(rows),
            "status": "pass"
        }))
        
    except Exception as e:
        safe_msg = sanitize_exception(e)
        print(json.dumps({"platform": "tiktok_ads", "status": "fail", "error": type(e).__name__, "message": safe_msg}))
        sys.exit(1)


def main():
    if os.environ.get("LIVE_CONNECTOR_VALIDATION") != "1":
        print("Error: LIVE_CONNECTOR_VALIDATION=1 environment variable is required to run this script.", file=sys.stderr)
        sys.exit(1)
        
    parser = argparse.ArgumentParser(description="Live Connector Validation")
    parser.add_argument("--platform", choices=["google_ads", "tiktok_ads"], required=True)
    parser.add_argument("--customer-id", help="Google Ads customer ID")
    parser.add_argument("--advertiser-id", help="TikTok Ads advertiser ID")
    
    args = parser.parse_args()
    
    if args.platform == "google_ads":
        cid = args.customer_id or os.environ.get("GOOGLE_ADS_CUSTOMER_ID")
        if not cid:
            print(json.dumps({"status": "fail", "error": "Missing customer_id"}))
            sys.exit(1)
        asyncio.run(validate_google_ads(cid))
    elif args.platform == "tiktok_ads":
        aid = args.advertiser_id or os.environ.get("TIKTOK_ADVERTISER_ID")
        if not aid:
            print(json.dumps({"status": "fail", "error": "Missing advertiser_id"}))
            sys.exit(1)
        asyncio.run(validate_tiktok_ads(aid))

if __name__ == "__main__":
    main()
