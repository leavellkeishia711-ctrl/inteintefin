from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import tenant_session, get_db_session
from app.core.config import settings
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

class UserCtx(BaseModel):
    user_id: str
    company_id: str
    role: str

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserCtx:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        company_id = payload.get("cid")
        role = payload.get("role", "member")
        if user_id is None or company_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    return UserCtx(
        user_id=user_id,
        company_id=company_id,
        role=role,
    )

from app.db.session import current_company_id

async def get_db(user: UserCtx = Depends(get_current_user)):
    async with tenant_session(user.company_id) as session:
        yield session

# Alias for backwards compatibility with what we just wrote
get_tenant_session = get_db

async def get_current_user_company_id(user: UserCtx = Depends(get_current_user)) -> str:
    return user.company_id

def require_roles(*roles: str):
    async def role_checker(user: UserCtx = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return user
    return role_checker

