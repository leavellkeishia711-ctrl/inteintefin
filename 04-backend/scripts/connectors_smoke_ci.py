import asyncio
import httpx
import os
import sys

async def run_smoke():
    # Use localhost:8000 when running from host
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    print("--- 1. Register & Login ---")
    async with httpx.AsyncClient(base_url=api_url) as client:
        email = "smoke_conn@example.com"
        pwd = "strongpass123"
        r1 = await client.post("/api/v1/auth/register", json={"email": email, "password": pwd})
        if r1.status_code not in (200, 201):
            print("Register failed:", r1.text)
            sys.exit(1)
        
        r2 = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
        if r2.status_code != 200:
            print("Login failed:", r2.text)
            sys.exit(1)
        token = r2.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        print("--- 2. Create connector ---")
        secret_key = "super_secret_keitaro_smoke_key_12345"
        r3 = await client.post("/api/v1/connectors/", json={
            "connector_name": "keitaro_smoke",
            "secret": secret_key,
            "sync_interval_minutes": 60
        })
        if r3.status_code != 201:
            print("Create connector failed (expected 201):", r3.status_code, r3.text)
            sys.exit(1)
        
        c_data = r3.json()
        if "secret" in c_data or secret_key in r3.text:
            print("CRITICAL: Secret leaked in response payload!")
            sys.exit(1)
        c_id = c_data["id"]
        
        # Save token and c_id for next step
        with open("smoke_state.txt", "w") as f:
            f.write(f"{token},{c_id},{email},{pwd}")

async def run_verify():
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    with open("smoke_state.txt", "r") as f:
        token, c_id, email, pwd = f.read().strip().split(",")
        
    print("--- 4. Login after API restart ---")
    async with httpx.AsyncClient(base_url=api_url) as client:
        r2 = await client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
        if r2.status_code != 200:
            print("Login failed after restart:", r2.text)
            sys.exit(1)
        token = r2.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        
        print("--- 5. Verify connector survived (Persistence check) ---")
        secret_key = "super_secret_keitaro_smoke_key_12345"
        r4 = await client.get("/api/v1/connectors/")
        if r4.status_code != 200:
            print("Get list failed:", r4.text)
            sys.exit(1)
            
        if secret_key in r4.text:
            print("CRITICAL: Secret leaked in list response!")
            sys.exit(1)
            
        conns = r4.json()
        found = next((c for c in conns if c["id"] == c_id), None)
        if not found:
            print("CRITICAL: Connector not found after API restart! Commit was lost.")
            sys.exit(1)
        if found["connector_name"] != "keitaro_smoke":
            print("CRITICAL: Connector data corrupted!")
            sys.exit(1)
            
        print("--- 6. Trigger sync ---")
        r5 = await client.post(f"/api/v1/connectors/{c_id}/sync")
        if r5.status_code != 200:
            print("Sync failed:", r5.text)
            sys.exit(1)
            
        print("--- 7. Wait and check sync fields ---")
        await asyncio.sleep(3)
        r6 = await client.get("/api/v1/connectors/")
        found = next((c for c in r6.json() if c["id"] == c_id), None)
        if found["last_attempted_sync"] is None:
            print("CRITICAL: last_attempted_sync was not updated after sync!")
            sys.exit(1)
            
        print(f"Status after sync: {found['status']}")
        # It could be 'failing' or 'unauthorized' or 'active', but last_attempted_sync must be set.
            
        print("Connectors smoke test PASSED.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        asyncio.run(run_verify())
    else:
        asyncio.run(run_smoke())
