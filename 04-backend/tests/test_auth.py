import pytest
from httpx import AsyncClient
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock
from app.core.config import settings

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_access_token_accepted(async_client: AsyncClient):
    from app.core.security import create_access_token
    import uuid
    from unittest.mock import patch
    
    test_sub = str(uuid.uuid4())
    test_cid = str(uuid.uuid4())
    access_token = create_access_token(test_sub, test_cid, "owner")
    
    # Since this is an E2E test and we don't have DB fixtures for this user,
    # we will just ensure it doesn't fail with 401 Unauthorized.
    # If it returns 404 (User not found), it means auth passed!
    res = await async_client.get(f"{settings.API_V1_STR}/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code in (200, 404)

@pytest.mark.asyncio
async def test_refresh_token_rejected_as_access(async_client: AsyncClient):
    from app.core.security import create_refresh_token
    import uuid
    test_sub = str(uuid.uuid4())
    test_cid = str(uuid.uuid4())
    refresh_token = create_refresh_token(test_sub, test_cid, "owner")
    res = await async_client.get(f"{settings.API_V1_STR}/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert res.status_code == 401
    
@pytest.mark.asyncio
async def test_refresh_endpoint(async_client: AsyncClient):
    from app.core.security import create_refresh_token
    import uuid
    test_sub = str(uuid.uuid4())
    test_cid = str(uuid.uuid4())
    refresh_token = create_refresh_token(test_sub, test_cid, "owner")
    
    with patch("app.services.telegram_bot.get_redis") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        mock_redis.get.return_value = None # not in denylist
        
        # Test valid refresh token
        res = await async_client.post(f"{settings.API_V1_STR}/auth/refresh", cookies={"refresh_token": refresh_token})
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        
        # Test old token in denylist
        mock_redis.get.return_value = b"1"
        res2 = await async_client.post(f"{settings.API_V1_STR}/auth/refresh", cookies={"refresh_token": refresh_token})
        assert res2.status_code == 401

@pytest.mark.asyncio
async def test_logout_endpoint(async_client: AsyncClient):
    from app.core.security import create_refresh_token
    import uuid
    test_sub = str(uuid.uuid4())
    test_cid = str(uuid.uuid4())
    refresh_token = create_refresh_token(test_sub, test_cid, "owner")
    
    with patch("app.services.telegram_bot.get_redis") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        
        res = await async_client.post(f"{settings.API_V1_STR}/auth/logout", cookies={"refresh_token": refresh_token})
        assert res.status_code == 200
        assert mock_redis.set.called

@pytest.mark.asyncio
async def test_invalid_jwt(async_client: AsyncClient):
    res = await async_client.post(f"{settings.API_V1_STR}/auth/refresh", cookies={"refresh_token": "invalid.jwt.here"})
    assert res.status_code == 401
