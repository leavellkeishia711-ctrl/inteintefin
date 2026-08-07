import asyncio
import httpx
import time
import sys
import uuid
import datetime

# Setup paths for imports
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../04-backend')))

from app.db.session import SessionLocal, engine
from app.db.models import Company, User, Transaction
from app.core.security import create_access_token
from app.core.config import settings

async def setup_test_data():
    async with SessionLocal() as session:
        # Create test company
        company = Company(name="Load Test Company", default_currency="USD")
        session.add(company)
        await session.commit()
        await session.refresh(company)

        # Create test user
        user = User(
            email=f"loadtest_{uuid.uuid4()}@example.com",
            hashed_password="fake",
            company_id=company.id
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Add some transactions
        tx = Transaction(
            company_id=company.id,
            amount=100.0,
            currency="USD",
            date=datetime.datetime.utcnow(),
            type="income",
            source="manual",
            external_id=str(uuid.uuid4())
        )
        session.add(tx)
        await session.commit()
        
        # Generate token
        token = create_access_token(user.id, company.id)
        return str(company.id), token

async def worker(worker_id: int, client: httpx.AsyncClient, num_requests: int, token: str):
    successes = 0
    failures = 0
    latencies = []
    
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(num_requests):
        try:
            start_t = time.time()
            resp = await client.get("http://127.0.0.1:8000/api/v1/reports/pnl", headers=headers, timeout=10.0)
            latencies.append(time.time() - start_t)
            
            if resp.status_code == 200:
                successes += 1
            else:
                failures += 1
        except Exception as e:
            failures += 1
    return successes, failures, latencies

async def main():
    concurrency = 50
    requests_per_worker = 10
    total_requests = concurrency * requests_per_worker
    
    print("Setting up test data...")
    company_id, token = await setup_test_data()
    
    print(f"Starting load test: {concurrency} workers, {requests_per_worker} requests each = {total_requests} total")
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(concurrency):
            tasks.append(worker(i, client, requests_per_worker, token))
        
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    total_successes = sum(r[0] for r in results)
    total_failures = sum(r[1] for r in results)
    all_latencies = []
    for r in results:
        all_latencies.extend(r[2])
    
    rps = total_requests / total_time
    all_latencies.sort()
    if all_latencies:
        idx = int(len(all_latencies) * 0.95)
        p95 = all_latencies[idx]
    else:
        p95 = 0.0
    
    print(f"Time: {total_time:.2f}s")
    print(f"Successes: {total_successes}")
    print(f"Failures (5xx or timeout): {total_failures}")
    print(f"RPS: {rps:.2f}")
    print(f"p95 Latency: {p95:.4f}s")
    
    # Check pool stats
    pool = engine.pool
    print(f"Pool stats - checkedin: {pool.checkedin()}, checkedout: {pool.checkedout()}")
    
    # Gate check
    if total_failures > 0:
        print("Test failed! Connection/pool errors or 5xx occurred.")
        sys.exit(1)
        
    if pool.checkedout() > 0:
        print(f"Test failed! Connection leak detected. checkedout: {pool.checkedout()}")
        sys.exit(1)
    
    print("Test passed! 0 connection pool errors.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
