from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.db.session import get_db_session
from app.db.models import User, Company
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.deps import get_current_user

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company_name: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    company_id: str

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate):
    import uuid
    from app.db.session import system_session
    
    # Check if user exists using system_session (bypasses RLS)
    async with system_session() as sys_db:
        result = await sys_db.execute(select(User).where(User.email == user_in.email))
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")
            
    # Generate IDs
    new_company_id = uuid.uuid4()
    new_user_id = uuid.uuid4()
    
    # Insert using system_session since new tenant creation bypasses RLS
    async with system_session() as db:
        async with db.begin():
            company = Company(id=new_company_id, name=user_in.company_name, base_currency="USD")
            db.add(company)
            
            user = User(
                id=new_user_id,
                email=user_in.email,
                password_hash=get_password_hash(user_in.password),
                name=user_in.name,
                role="owner",
                company_id=new_company_id
            )
            db.add(user)
        
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        company_id=str(user.company_id)
    )

@router.post("/login", response_model=Token)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    from app.db.session import system_session
    
    # Lookup user using system_session to bypass RLS since company_id is unknown
    async with system_session() as sys_db:
        result = await sys_db.execute(select(User).where(User.email == form_data.username))
        user = result.scalars().first()
        
        if not user or not verify_password(form_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        from app.core.security import create_refresh_token
        access_token = create_access_token(
            subject=str(user.id),
            company_id=str(user.company_id),
            role=user.role
        )
        refresh_token = create_refresh_token(
            subject=str(user.id),
            company_id=str(user.company_id),
            role=user.role
        )
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60)
        return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    from app.services.telegram_bot import get_redis
    from jose import jwt, JWTError
    from app.core.config import settings
    
    try:
        redis = await get_redis()
        is_denied = await redis.get(f"denylist:{refresh_token}")
        if is_denied:
            raise HTTPException(status_code=401, detail="Token revoked")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Service Unavailable")
        
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
        company_id = payload.get("cid")
        role = payload.get("role")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    try:
        await redis.set(f"denylist:{refresh_token}", "1")
        await redis.expire(f"denylist:{refresh_token}", 30*24*60*60)
    except Exception:
        raise HTTPException(status_code=503, detail="Service Unavailable")
        
    from app.core.security import create_refresh_token
    access_token = create_access_token(subject=user_id, company_id=company_id, role=role)
    new_refresh_token = create_refresh_token(subject=user_id, company_id=company_id, role=role)
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60)
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        from app.services.telegram_bot import get_redis
        try:
            redis = await get_redis()
            await redis.set(f"denylist:{refresh_token}", "1")
            await redis.expire(f"denylist:{refresh_token}", 30*24*60*60)
        except Exception:
            raise HTTPException(status_code=503, detail="Service Unavailable")
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")
    return {"status": "success"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)): # it's UserCtx
    from app.db.session import tenant_session
    async with tenant_session(current_user.company_id) as db:
        result = await db.execute(select(User).where(User.id == current_user.user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            name=user.name,
            role=user.role,
            company_id=str(user.company_id)
        )
