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
    
    async with tenant_session(str(company_a_id)) as db:
        await db.execute(text(
            "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
        ), {"id": company_a_id, "name": "Company A", "currency": "USD"})
        
        await db.execute(text(
            "INSERT INTO users (id, company_id, name, email, password_hash, role, preferred_language) VALUES (:id::UUID, :company_id::UUID, :name::VARCHAR, :email::VARCHAR, :password_hash::VARCHAR, :role::VARCHAR, :preferred_language::VARCHAR) RETURNING users.created_at, users.updated_at"
        ), {
            "id": user_a_id, 
            "company_id": company_a_id, 
            "name": "A", 
            "email": "a@example.com", 
            "password_hash": "hash123", 
            "role": "owner",
            "preferred_language": None
        })
        print("User inserted via raw SQL with ONE null")
    
    print("Session exited")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
