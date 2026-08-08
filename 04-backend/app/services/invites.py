import secrets
import hashlib
from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Invite, User, Company
from app.core.security import get_password_hash
from fastapi import HTTPException

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

async def create_invite(db: AsyncSession, company_id: uuid.UUID, email: str, role: str, invited_by: uuid.UUID) -> tuple[Invite, str]:
    # Check if user already exists in this company
    stmt = select(User).where(User.company_id == company_id, User.email == email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists in the company")
        
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)
    
    # Check if invite already exists, we could soft delete it or update, but let's just create a new one
    # Note: there is no unique constraint on email+company_id without expires_at check, 
    # but the index ix_invites_company_email exists.
    
    invite = Invite(
        company_id=company_id,
        email=email,
        role=role,
        token_hash=token_hash,
        invited_by=invited_by,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=72)
    )
    db.add(invite)
    await db.flush()
    return invite, raw_token

async def get_invite_info(db: AsyncSession, token: str) -> dict:
    token_hash = hash_token(token)
    stmt = select(Invite, Company.name).join(Company, Invite.company_id == Company.id).where(Invite.token_hash == token_hash)
    result = (await db.execute(stmt)).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    invite, company_name = result
    
    if invite.status != "pending":
        raise HTTPException(status_code=400, detail="Invite already used or revoked")
        
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite expired")
        
    return {
        "email": invite.email,
        "company_name": company_name,
        "role": invite.role
    }

async def accept_invite(sys_db: AsyncSession, token: str, name: str, password: str) -> User:
    token_hash = hash_token(token)
    stmt = select(Invite).where(Invite.token_hash == token_hash)
    invite = (await sys_db.execute(stmt)).scalar_one_or_none()
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    if invite.status != "pending":
        raise HTTPException(status_code=400, detail="Invite already used or revoked")
        
    if invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite expired")
        
    # Check if user already exists
    user_stmt = select(User).where(User.company_id == invite.company_id, User.email == invite.email)
    existing_user = (await sys_db.execute(user_stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
        
    user = User(
        company_id=invite.company_id,
        email=invite.email,
        name=name,
        password_hash=get_password_hash(password),
        role=invite.role
    )
    sys_db.add(user)
    
    invite.status = "accepted"
    invite.accepted_at = datetime.now(timezone.utc)
    
    await sys_db.flush()
    return user

async def list_company_invites(db: AsyncSession, company_id: uuid.UUID):
    stmt = select(Invite).where(Invite.company_id == company_id, Invite.status != "revoked")
    result = (await db.execute(stmt)).scalars().all()
    return result

async def revoke_invite(db: AsyncSession, company_id: uuid.UUID, invite_id: uuid.UUID):
    stmt = select(Invite).where(Invite.id == invite_id, Invite.company_id == company_id)
    invite = (await db.execute(stmt)).scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
        
    if invite.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot revoke invite in status {invite.status}")
        
    invite.status = "revoked"
    await db.flush()
    return invite
