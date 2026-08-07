import asyncio
import httpx
import time
import sys

async def worker(worker_id: int, client: httpx.AsyncClient, num_requests: int):
    successes = 0
    failures = 0
    for i in range(num_requests):
        try:
            resp = await client.get("http://127.0.0.1:8000/api/v1/health", timeout=10.0)
            if resp.status_code == 200:
                successes += 1
            else:
                failures += 1
        except Exception as e:
            failures += 1
    return successes, failures

async def main():
    concurrency = 100
    requests_per_worker = 5
    total_requests = concurrency * requests_per_worker
    
    print(f"Starting load test: {concurrency} workers, {requests_per_worker} requests each = {total_requests} total")
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(concurrency):
            tasks.append(worker(i, client, requests_per_worker))
        
        results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    total_successes = sum(s for s, f in results)
    total_failures = sum(f for s, f in results)
    
    print(f"Time: {total_time:.2f}s")
    print(f"Successes: {total_successes}")
    print(f"Failures: {total_failures}")
    
    if total_failures > 0:
        print("Test failed! Had connection/pool errors.")
        sys.exit(1)
    
    print("Test passed! 0 connection pool errors.")
    sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
