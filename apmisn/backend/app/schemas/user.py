"""
Pydantic schemas for User read/write payloads, profile, and settings.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    is_active: bool
    is_superuser: bool
    is_email_verified: bool
    created_at: datetime
    updated_at: datetime


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str | None
    status: str
    is_email_verified: bool
    is_superuser: bool
    roles: list[str] = []
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = None


class UserStatusUpdate(BaseModel):
    status: str  # active, suspended, disabled


class AvatarUpdate(BaseModel):
    avatar_url: str
