"""
Test: SQLAlchemy ORM session.add(User(...)) — the actual failing case.
"""
import asyncio
import uuid
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Must import session.py first (it does the monkey-patch)
from app.db.session import engine, async_session_maker
from app.db.models.users import User
from app.db.models.companies import Company
from sqlalchemy import text

async def main():
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
    print(f"Company ID: {company_id}")
    print(f"User ID: {user_id}")
    
    async with async_session_maker() as session:
        async with session.begin():
            # Set tenant context
            await session.execute(text("SET LOCAL ROLE app_user"))
            await session.execute(
                text("SELECT set_config('app.company_id', :cid, true)"),
                {"cid": str(company_id)}
            )
            print("Tenant context set")
            
            # Insert company via text (known to work)
            await session.execute(text(
                "INSERT INTO companies (id, name, base_currency) VALUES (:id, :name, :currency)"
            ), {"id": company_id, "name": "ORM_Test", "currency": "USD"})
            print("Company inserted via text")
            
            # Now try ORM User
            user = User(
                id=user_id,
                company_id=company_id,
                name="ORMUser",
                email="orm@test.com",
                password_hash="hash789",
                role="owner",
            )
            session.add(user)
            print("User added to session, about to flush...")
            
            # Force flush to see the ORM SQL
            try:
                await session.flush()
                print(f"FLUSH succeeded! user.created_at={user.created_at}")
            except Exception as e:
                print(f"FLUSH FAILED: {type(e).__name__}: {e}")
                raise
    
    print("Session closed successfully")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
