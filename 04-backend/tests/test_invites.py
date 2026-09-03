import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_invites_happy_path(client_a: AsyncClient):
    # 1. Create invite (owner)
    res = await client_a.post("/api/v1/auth/invite", json={"email": "new_team@test.com", "role": "team_lead"})
    assert res.status_code == 200, res.text
    token = res.json()["token"]
    
    # 2. Get invite info (public)
    res_info = await client_a.get(f"/api/v1/auth/invite/{token}")
    assert res_info.status_code == 200, res_info.text
    info = res_info.json()
    assert info["email"] == "new_team@test.com"
    assert info["role"] == "team_lead"
    
    # 3. Accept invite (public)
    res_accept = await client_a.post(f"/api/v1/auth/invite/{token}/accept", json={"name": "New Team Lead", "password": "password123"})
    print("RES_ACCEPT:", res_accept.status_code, res_accept.text)
    assert res_accept.status_code == 200, res_accept.text
    
    # 4. Try to accept again -> 400
    res_accept_2 = await client_a.post(f"/api/v1/auth/invite/{token}/accept", json={"name": "New Team Lead 2", "password": "password123"})
    assert res_accept_2.status_code == 400
    assert "Invite already used or revoked" in res_accept_2.json()["detail"]
    
    # 5. List invites
    res_list = await client_a.get("/api/v1/auth/invites")
    assert res_list.status_code == 200
    invites = res_list.json()
    assert len(invites) >= 1
    
    # 6. Revoke an invite (create a new one and revoke it)
    res2 = await client_a.post("/api/v1/auth/invite", json={"email": "revoke@test.com", "role": "media_buyer"})
    invite_token = res2.json()["token"]
    
    # list to get ID
    res_list2 = await client_a.get("/api/v1/auth/invites")
    invites2 = res_list2.json()
    revoke_id = next(i["id"] for i in invites2 if i["email"] == "revoke@test.com")
    
    # revoke
    res_revoke = await client_a.delete(f"/api/v1/auth/invites/{revoke_id}")
    assert res_revoke.status_code == 200
    
    # try to accept revoked
    res_accept_rev = await client_a.post(f"/api/v1/auth/invite/{invite_token}/accept", json={"name": "R", "password": "pass"})
    assert res_accept_rev.status_code == 400
    assert "Invite already used or revoked" in res_accept_rev.json()["detail"]

@pytest.mark.asyncio
async def test_invites_media_buyer_forbidden(app):
    import httpx
    import uuid
    from app.core.security import create_access_token
    token = create_access_token(
        subject=str(uuid.uuid4()), 
        company_id=str(uuid.uuid4()), 
        role="media_buyer"
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        res = await client.post("/api/v1/auth/invite", json={"email": "test@test.com", "role": "media_buyer"})
        assert res.status_code == 403
        
@pytest.mark.asyncio
async def test_invites_team_lead_forbidden(app):
    import httpx
    import uuid
    from app.core.security import create_access_token
    token = create_access_token(
        subject=str(uuid.uuid4()), 
        company_id=str(uuid.uuid4()), 
        role="team_lead"
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update({"Authorization": f"Bearer {token}"})
        res = await client.post("/api/v1/auth/invite", json={"email": "test@test.com", "role": "media_buyer"})
        assert res.status_code == 403

@pytest.mark.asyncio
async def test_invites_cross_tenant(client_a: AsyncClient, client_b: AsyncClient):
    # Create invite in A
    await client_a.post("/api/v1/auth/invite", json={"email": "cross@test.com", "role": "creative"})
    
    # List in B - should not see A's invites
    res_list_b = await client_b.get("/api/v1/auth/invites")
    assert res_list_b.status_code == 200
    invites_b = res_list_b.json()
    assert not any(i["email"] == "cross@test.com" for i in invites_b)

@pytest.mark.asyncio
async def test_duplicate_invite_email(client_a: AsyncClient):
    await client_a.post("/api/v1/auth/invite", json={"email": "dup@test.com", "role": "creative"})
    res = await client_a.post("/api/v1/auth/invite", json={"email": "dup@test.com", "role": "creative"})
    assert res.status_code == 200 # Allowed to have multiple invites for the same email? Or wait, in create_invite we only check User table.
    
    # We must mock accept_invite to create a user and then fail on second invite
    # Actually, in create_invite:
    # "Не допускай создание инвайта для уже существующего пользователя той же компании."
    # We check the User table. Let's create a user.
    res_accept = await client_a.post(f"/api/v1/auth/invite/{res.json()['token']}/accept", json={"name": "Dup", "password": "pass"})
    assert res_accept.status_code == 200
    
    # Now creating invite for dup@test.com should fail
    res_fail = await client_a.post("/api/v1/auth/invite", json={"email": "dup@test.com", "role": "creative"})
    assert res_fail.status_code == 400
    assert "already exists in the company" in res_fail.text

