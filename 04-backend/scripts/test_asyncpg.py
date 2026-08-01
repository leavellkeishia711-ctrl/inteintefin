"""Test: compute hash BEFORE opening session."""
import asyncio
import sys
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.db.session import tenant_session, engine
from app.db.models import Company, User
from app.core.security import get_password_hash

async def run():
    company_a_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    
    # Compute hash BEFORE opening DB session
    print("Computing password hash...")
    pw_hash = get_password_hash("test")
    print(f"Hash computed: {pw_hash[:20]}...")
    
    print("=== Opening tenant_session ===")
    async with tenant_session(str(company_a_id)) as db:
        print("=== Inside tenant_session ===")
        company = Company(id=company_a_id, name="Company A", base_currency="USD")
        db.add(company)
        
        user = User(
            id=user_a_id, email="a@example.com", 
            password_hash=pw_hash,
            name="A", role="owner", company_id=company_a_id
        )
        db.add(user)
        print("=== About to exit (flush+commit) ===")
    
    print("=== SUCCESS! ===")
    
    # Cleanup
    async with tenant_session(str(company_a_id)) as db:
        from sqlalchemy import text
        await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_a_id)})
        await db.execute(text("DELETE FROM companies WHERE id = :id"), {"id": str(company_a_id)})
    print("=== Cleanup done ===")
    
    await engine.dispose()
    print("ALL OK!")

if __name__ == '__main__':
    asyncio.run(run())
