from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email_id: EmailStr
    user_name: Optional[str] = None
    user_pic: Optional[str] = None

class UserCreate(UserBase):
    user_id: str

class UserUpdate(BaseModel):
    user_name: Optional[str] = None
    user_pic: Optional[str] = None
    last_accessed: Optional[datetime] = None

class UserInDB(UserBase):
    id: int
    user_id: str
    first_logged_in: datetime
    last_accessed: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class User(UserInDB):
    pass

class TokenData(BaseModel):
    user_id: str
    email: str
    exp: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class IssuedTokenBase(BaseModel):
    email_id: EmailStr
    session_id: str
    user_id: str
    token_type: str = "access"

class IssuedTokenCreate(IssuedTokenBase):
    token: str
    expires_at: Optional[datetime] = None

class IssuedTokenInDB(IssuedTokenBase):
    id: int
    token: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class IssuedToken(IssuedTokenInDB):
    pass

class GoogleUserInfo(BaseModel):
    sub: str  # Google user ID
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    email_verified: Optional[bool] = None

class AuthResponse(BaseModel):
    message: str
    user: User
    access_token: str
    token_type: str = "bearer"

class LogoutResponse(BaseModel):
    message: str
    
class UserResponse(BaseModel):
    user: User
    message: str = "User retrieved successfully"