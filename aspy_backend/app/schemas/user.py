from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SocialLoginRequest(BaseModel):
    provider: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    token: Optional[str] = None
    code: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    user_type: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    username: str
    email: EmailStr