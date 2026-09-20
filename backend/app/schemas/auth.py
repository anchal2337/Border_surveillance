from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from backend.app.core.constants import UserRole

# -----------------------------------------------------------------------------
# Authentication & Token Schemas
# -----------------------------------------------------------------------------
class UserLogin(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["admin123"])

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    username: str
    full_name: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None

# -----------------------------------------------------------------------------
# User Profile & Management Schemas
# -----------------------------------------------------------------------------
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["sentry_guard_1"])
    email: EmailStr = Field(..., examples=["guard1@ibvap.mil"])
    password: str = Field(..., min_length=6, examples=["SentryGuard@2026"])
    full_name: str = Field(..., examples=["Constable Rajesh Kumar"])
    role: UserRole = Field(default=UserRole.OPERATOR, examples=[UserRole.OPERATOR])
    badge_number: Optional[str] = Field(None, examples=["BOP-G-402"])
    department: str = Field(default="Border Patrol Sentry", examples=["Border Patrol Sentry"])

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    badge_number: Optional[str] = None
    department: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RoleUpdate(BaseModel):
    role: UserRole = Field(..., examples=[UserRole.COMMANDER])
