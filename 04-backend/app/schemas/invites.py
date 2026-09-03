from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class InviteCreate(BaseModel):
    email: EmailStr
    role: str

class InviteResponse(BaseModel):
    token: str

class InviteInfo(BaseModel):
    email: str
    company_name: str
    role: str

class InviteAccept(BaseModel):
    name: str
    password: str

class InviteListResponse(BaseModel):
    id: str
    email: str
    role: str
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime]
