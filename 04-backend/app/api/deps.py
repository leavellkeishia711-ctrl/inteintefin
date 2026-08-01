from fastapi import Request, HTTPException, status
from app.db.session import tenant_session
import uuid

async def get_tenant_db(request: Request):
    """
    Extracts the company_id from the JWT token in the request state,
    and returns an AsyncSession scoped to that tenant via RLS.
    """
    # Assuming the authentication middleware sets request.state.company_id
    company_id = getattr(request.state, "company_id", None)
    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Company ID not found in session",
        )
    
    # We yield the session from the async context manager
    async with tenant_session(str(company_id)) as session:
        yield session
