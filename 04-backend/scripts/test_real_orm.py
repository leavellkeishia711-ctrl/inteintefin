"""
Test: ORM insert using the REAL tenant_session and the REAL User model from the app.
"""
import asyncio
import uuid
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.db.session import tenant_session, engine
from app.db.models.users import User
from sqlalchemy import text

async def main():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    print(f"Company ID: {company_id}")
    print(f"User ID: {user_id}")
    
    async with tenant_session(str(company_id)) as db:
        # Insert company first (as app_user via RLS - but companies has its own policy)
        await db.execute(text(
            "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
        ), {"id": company_id, "name": "RealORM_Test", "currency": "USD"})
        print("Company inserted")
        
        # ORM User insert
        user = User(
            id=user_id,
            company_id=company_id,
            name="RealORMUser",
            email="realorm@test.com",
            password_hash="hash_real_123",
            role="owner",
        )
        db.add(user)
        print("User added, flushing...")
        await db.flush()
        print(f"FLUSH OK! created_at={user.created_at}")
    
    print("tenant_session exited OK")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
