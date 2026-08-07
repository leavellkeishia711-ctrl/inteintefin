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
                email="tg@test.com",
                name="TG User",
                password_hash="test",
                role="admin"
            )
            db.add(user)
            
    token = "testtoken123"
    await mock_redis.set(f"telegram_link:{token}", str(user_id))
    
    chat_id = 123456789
    
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
