from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user, UserCtx, get_tenant_session, require_roles
from app.db.session import system_session, get_db_session
from app.schemas.invites import InviteCreate, InviteResponse, InviteInfo, InviteAccept, InviteListResponse
from app.services.invites import create_invite, get_invite_info, accept_invite, list_company_invites, revoke_invite
import uuid

router = APIRouter()

@router.post("/invite", response_model=InviteResponse)
async def create_new_invite(
    data: InviteCreate,
    user: UserCtx = Depends(require_roles("owner", "cfo")),
    db: AsyncSession = Depends(get_tenant_session)
):
    if data.role not in ['owner','cfo','team_lead','media_buyer','farmer','processor','creative']:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Use system session to verify user doesn't already exist and create invite? 
    # Actually create_invite needs sys_db because it queries User which is tenant_scoped, but get_tenant_session works too.
    # Wait, create_invite uses User and Invite models. If db is tenant_session, User query works.
    invite, token = await create_invite(db, uuid.UUID(user.company_id), data.email, data.role, uuid.UUID(user.user_id))
    return InviteResponse(token=token)

@router.get("/invite/{token}", response_model=InviteInfo)
async def get_invite(token: str):
    async with system_session() as db:
        return await get_invite_info(db, token)

@router.post("/invite/{token}/accept")
async def accept_invite_endpoint(token: str, data: InviteAccept):
    async with system_session() as sys_db:
        async with sys_db.begin():
            user = await accept_invite(sys_db, token, data.name, data.password)
            return {"status": "success", "user_id": str(user.id)}

@router.get("/invites", response_model=list[InviteListResponse])
async def list_invites(
    user: UserCtx = Depends(require_roles("owner", "cfo")),
    db: AsyncSession = Depends(get_tenant_session)
):
    invites = await list_company_invites(db, uuid.UUID(user.company_id))
    return [
        InviteListResponse(
            id=str(inv.id),
            email=inv.email,
            role=inv.role,
            status=inv.status,
            expires_at=inv.expires_at,
            accepted_at=inv.accepted_at
        ) for inv in invites
    ]

@router.delete("/invites/{id}")
async def revoke_invite_endpoint(
    id: str,
    user: UserCtx = Depends(require_roles("owner", "cfo")),
    db: AsyncSession = Depends(get_tenant_session)
):
    await revoke_invite(db, uuid.UUID(user.company_id), uuid.UUID(id))
    return {"status": "revoked"}
