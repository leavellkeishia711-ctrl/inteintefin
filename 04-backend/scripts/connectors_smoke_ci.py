import asyncio
import httpx

async def run_smoke():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Register
        email = "smoke_conn@example.com"
        pwd = "strongpass123"
        r1 = await client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
        if r1.status_code != 200:
            print("Register failed:", r1.text)
            exit(1)
        
        # Login
        r2 = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
        if r2.status_code != 200:
            print("Login failed:", r2.text)
            exit(1)
        token = r2.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        # Create connector
        secret_key = "super_secret_keitaro_smoke_key_12345"
        r3 = await client.post("/api/v1/connectors/", json={
            "connector_name": "keitaro_smoke",
            "secret": secret_key,
            "sync_interval_minutes": 60
        })
        if r3.status_code != 200:
            print("Create connector failed:", r3.text)
            exit(1)
        
        c_data = r3.json()
        if "secret" in c_data or secret_key in r3.text:
            print("CRITICAL: Secret leaked in response payload!")
            exit(1)
        c_id = c_data["id"]
        
        # Get list
        r4 = await client.get("/api/v1/connectors/")
        if r4.status_code != 200:
            print("Get list failed:", r4.text)
            exit(1)
            
        if secret_key in r4.text:
            print("CRITICAL: Secret leaked in list response!")
            exit(1)
            
        # Trigger sync
        r5 = await client.post(f"/api/v1/connectors/{c_id}/sync")
        if r5.status_code != 200:
            print("Sync failed:", r5.text)
            exit(1)
            
        print("Connectors smoke test PASSED.")

if __name__ == "__main__":
    asyncio.run(run_smoke())
