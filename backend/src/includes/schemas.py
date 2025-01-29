from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional
import re
from uuid import UUID

ALLOWED_DOMAINS = ["manifesto.it", "isagog.com"]

class UserBase(BaseModel):
    email: EmailStr

    @field_validator('email')
    def validate_email_domain(cls, v):
        domain = v.split('@')[1].lower()
        if domain not in ALLOWED_DOMAINS:
            raise ValueError(f"Email domain must be one of: {', '.join(ALLOWED_DOMAINS)}")
        return v

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class User(UserBase):
    id: UUID
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

class EmailVerificationConfirm(BaseModel):
    token: str
