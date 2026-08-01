import asyncio
import uuid
import sys
from app.db.session import tenant_session, engine
from app.db.models import Company, User
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
        company = Company(id=company_a_id, name="Company A", base_currency="USD")
        db.add(company)
        print("Company added to session")
        user = User(
            id=user_a_id, email="a@example.com", password_hash="hash123",
            name="A", role="owner", company_id=company_a_id
        )
        db.add(user)
        print("User added to session")
    
    print("Session exited (commit successful)")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
