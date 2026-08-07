import asyncio
import httpx
import sys
import time
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../04-backend')))

from app.db.session import SessionLocal
from app.core.config import settings
from sqlalchemy import text

async def check_tokens_not_used():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM telegram_link_tokens WHERE used_at IS NOT NULL"))
        count = result.scalar()
        return count

async def check_workers():
    # Attempt to check if gunicorn/uvicorn is running with 2 workers using ps or similar 
    # but we are hitting it from outside the container, so we just check if it answers.
    pass

async def main():
    webhook_url = "http://127.0.0.1:8000/api/v1/webhooks/telegram"
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    
    headers = {
        "x-telegram-bot-api-secret-token": secret
    }
    
    payload_link = {
        "message": {
            "chat": {"id": 12345},
            "text": "/link test_token"
        }
    }
    
    payload_status = {
        "message": {
            "chat": {"id": 12345},
            "text": "/status"
        }
    }
    
    concurrency = 100
    
    async with httpx.AsyncClient() as client:
        print("Running 100 parallel /link requests to webhook...")
        
        tasks = []
        for i in range(concurrency):
            tasks.append(client.post(webhook_url, json=payload_link, headers=headers, timeout=10.0))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        status_codes = []
        for r in results:
            if isinstance(r, httpx.Response):
                status_codes.append(r.status_code)
            else:
                status_codes.append(type(r).__name__)
                
        print(f"Status codes distribution (/link): {dict((x, status_codes.count(x)) for x in set(status_codes))}")
        
        non_503s = [s for s in status_codes if s != 503]
        if non_503s:
            print(f"FAILED: Found non-503 responses for /link: {non_503s}")
            sys.exit(1)
            
        # Check that tokens are not used
        used_tokens_count = await check_tokens_not_used()
        if used_tokens_count > 0:
            print(f"FAILED: {used_tokens_count} link tokens were marked as used, but Redis was down!")
            sys.exit(1)
            
        # Test /status
        print("Testing /status best-effort limiter...")
        resp = await client.post(webhook_url, json=payload_status, headers=headers, timeout=10.0)
        
        # We expect /status to not return 503 even if Redis is down, it should use in-memory and return 200 (or something)
        print(f"/status response code: {resp.status_code}")
        if resp.status_code == 503:
            print("FAILED: /status returned 503 when Redis is down. It should use in-memory fallback.")
            sys.exit(1)

        print("PASSED: All checks passed. 503 for /link, in-memory for /status, no tokens consumed.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
