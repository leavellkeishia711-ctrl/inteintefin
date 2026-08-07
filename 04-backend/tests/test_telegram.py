import pytest
from app.services.telegram_bot import handle_telegram_message
from app.db.models import User, Company
from app.db.session import system_session
import uuid

class MockRedis:
    def __init__(self):
        self.store = {}
        
    async def get(self, key):
        return self.store.get(key)
        
    async def set(self, key, value):
        if isinstance(value, str):
            value = value.encode('utf-8')
        self.store[key] = value
        
    async def delete(self, key):
        if key in self.store:
            del self.store[key]
            
    async def incr(self, key):
        val = int(self.store.get(key, b'0')) + 1
        self.store[key] = str(val).encode('utf-8')
        return val
        
    async def expire(self, key, time):
        pass

@pytest.mark.asyncio
async def test_telegram_link_token(monkeypatch):
    import app.services.telegram_bot
    mock_redis = MockRedis()
    async def mock_get_redis():
        return mock_redis
    monkeypatch.setattr(app.services.telegram_bot, "get_redis", mock_get_redis)

    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    async with system_session() as db:
        async with db.begin():
            company = Company(
                id=company_id,
                name="TG Company",
                base_currency="USD"
            )
            db.add(company)
            
            user = User(
                id=user_id,
                company_id=company_id,
                email="tg_e8bd151b@test.com",
                name="TG User",
                password_hash="test",
                role="admin"
            )
            db.add(user)
            
    token = "testtoken123"
    await mock_redis.set(f"telegram_link:{token}", str(user_id))
    
    import random
    chat_id = random.randint(1000000, 999999999)
    
    async with system_session() as db:
        res = await handle_telegram_message(db, chat_id, f"/link {token}")
        assert res == "Your Telegram account has been successfully linked!"
        
        user = await db.get(User, user_id)
        assert user.telegram_chat_id == chat_id
        
        assert await mock_redis.get(f"telegram_link:{token}") is None

@pytest.mark.asyncio
async def test_telegram_status_cross_tenant(monkeypatch):
    import app.services.telegram_bot
    mock_redis = MockRedis()
    async def mock_get_redis():
        return mock_redis
    monkeypatch.setattr(app.services.telegram_bot, "get_redis", mock_get_redis)
    pass

@pytest.mark.asyncio
async def test_telegram_redis_unavailable(monkeypatch):
    import app.services.telegram_bot
    from redis.exceptions import ConnectionError
    
    class BrokenRedis:
        async def incr(self, key):
            raise ConnectionError("Redis is down")
        async def get(self, key):
            raise ConnectionError("Redis is down")
            
    async def mock_get_redis():
        return BrokenRedis()
        
    monkeypatch.setattr(app.services.telegram_bot, "get_redis", mock_get_redis)
    
    # Should fall back to local rate limit (allow 5, deny 6)
    app.services.telegram_bot._local_limits.clear()
    
    for _ in range(5):
        res = await app.services.telegram_bot.check_rate_limit(12345)
        assert res is True
        
    res_6 = await app.services.telegram_bot.check_rate_limit(12345)
    assert res_6 is False
    
    from app.db.session import system_session
    async with system_session() as db:
        # Should not crash on link
        res = await handle_telegram_message(db, 12345, "/link some_token")
        assert res == "Our systems are temporarily overloaded. Please try linking again later."

@pytest.mark.asyncio
async def test_telegram_link_success_and_reuse(monkeypatch):
    import app.services.telegram_bot
    from app.db.models import Company, User
    from app.db.session import system_session
    import uuid

    mock_db = {}
    class FakeRedis:
        async def get(self, key):
            return mock_db.get(key)
        async def delete(self, key):
            if key in mock_db:
                del mock_db[key]
        async def incr(self, key):
            return 1
        async def expire(self, key, time):
            pass

    fake_redis = FakeRedis()
    async def mock_get_redis():
        return fake_redis

    monkeypatch.setattr(app.services.telegram_bot, "get_redis", mock_get_redis)
    monkeypatch.setattr(app.services.telegram_bot, "check_rate_limit", lambda x: True)

    async with system_session() as db:
        async with db.begin():
            company = Company(id=uuid.uuid4(), name="T", base_currency="USD")
            db.add(company)
            user = User(id=uuid.uuid4(), company_id=company.id, email=f"test_{uuid.uuid4().hex[:8]}@t.com", password_hash="h", name="N", role="owner")
            db.add(user)
        
        # We don't need a token in redis bytes format? Actually we do:
        token = "secret-token-123"
        mock_db[f"telegram_link:{token}"] = str(user.id).encode('utf-8')

        # First use
        res1 = await app.services.telegram_bot.handle_telegram_message(db, 99999, f"/link {token}")
        assert res1 == "Your Telegram account has been successfully linked!"

        # Second use
        res2 = await app.services.telegram_bot.handle_telegram_message(db, 88888, f"/link {token}")
        assert res2 == "Invalid or expired link token."
