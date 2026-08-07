import asyncio
import httpx
import sys
import time

async def main():
    webhook_url = "http://127.0.0.1:8000/api/v1/webhooks/telegram" # check path
    # Let's verify the exact path, wait. The router in webhooks.py has @router.post("/telegram"). So /api/v1/webhooks/telegram
    
    headers = {
        "x-telegram-bot-api-secret-token": "test_secret"
    }
    
    payload = {
        "message": {
            "chat": {"id": 12345},
            "text": "/link test_token"
        }
    }
    
    concurrency = 100
    
    async with httpx.AsyncClient() as client:
        print("Running 100 parallel /link requests to webhook...")
        
        # Redis is expected to be stopped in the CI pipeline before running this script
        
        tasks = []
        for i in range(concurrency):
            tasks.append(client.post(webhook_url, json=payload, headers=headers, timeout=10.0))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        status_codes = []
        for r in results:
            if isinstance(r, httpx.Response):
                status_codes.append(r.status_code)
            else:
                status_codes.append(type(r).__name__)
                
        print(f"Status codes distribution: {dict((x, status_codes.count(x)) for x in set(status_codes))}")
        
        # We expect all to be 503 because Redis is down and rate limiter fails closed.
        non_503s = [s for s in status_codes if s != 503]
        if non_503s:
            print(f"FAILED: Found non-503 responses: {non_503s}")
            sys.exit(1)
        else:
            print("PASSED: All requests correctly returned 503 Service Unavailable when Redis is down.")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
