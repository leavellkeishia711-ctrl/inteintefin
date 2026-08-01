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
    print("Hash computed")
    
    async with tenant_session(str(company_a_id)) as db:
        print("Inside tenant session")
        await db.execute(text(
            "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
        ), {"id": company_a_id, "name": "Company A", "currency": "USD"})
        print("Company inserted via raw SQL")
        
        await db.execute(text(
            """INSERT INTO users (id, company_id, name, email, password_hash, role) 
            VALUES (:id, :cid, :name, :email, :pw, :role) RETURNING created_at, updated_at"""
        ), {
            "id": user_a_id, "cid": company_a_id, "name": "A", "email": "a@example.com",
            "pw": "hash123", "role": "owner"
        })
        print("User inserted via raw SQL")
    
    print("Session exited (commit successful)")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
