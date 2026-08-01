import asyncio
import uuid
import sys
from app.db.session import tenant_session, engine
from sqlalchemy import text
from app.core.security import get_password_hash

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    company_a_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    
    print(f"Company ID: {company_a_id}")
    print(f"User ID: {user_a_id}")
    
    pw_hash = get_password_hash("test")
    
    async with tenant_session(str(company_a_id)) as db:
        await db.execute(text(
            "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
        ), {"id": company_a_id, "name": "Company A", "currency": "USD"})
        
        await db.execute(text(
            "INSERT INTO users (id, company_id, name, email, password_hash, role, preferred_language, telegram_user_id, telegram_chat_id, telegram_linked_at, deleted_at) VALUES (:id::UUID, :company_id::UUID, :name::VARCHAR, :email::VARCHAR, :password_hash::VARCHAR, :role::VARCHAR, :preferred_language::VARCHAR, :telegram_user_id::BIGINT, :telegram_chat_id::BIGINT, :telegram_linked_at::TIMESTAMP WITH TIME ZONE, :deleted_at::TIMESTAMP WITH TIME ZONE) RETURNING users.created_at, users.updated_at"
        ), {
            "id": user_a_id, 
            "company_id": company_a_id, 
            "name": "A", 
            "email": "a@example.com", 
            "password_hash": "hash123", 
            "role": "owner",
            "preferred_language": None,
            "telegram_user_id": None,
            "telegram_chat_id": None,
            "telegram_linked_at": None,
            "deleted_at": None
        })
        print("User inserted via raw SQL with exact ORM query")
    
    print("Session exited (commit successful)")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
