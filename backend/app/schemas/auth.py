"""
Pydantic schemas for the full authentication & authorization system.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr


# ──────────────────────── Auth Schemas ────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MFARequiredResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str


class MFAVerifyLoginRequest(BaseModel):
    mfa_token: str
    code: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class EmailVerifyRequest(BaseModel):
    token: str


class MFASetupResponse(BaseModel):
    secret: str
    message: str


class MFAEnableRequest(BaseModel):
    code: str


class MFADisableRequest(BaseModel):
    code: str


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None


# ──────────────────────── Session Schemas ────────────────────────

class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    expires_at: datetime
    is_active: bool
    created_at: datetime


# ──────────────────────── Generic Responses ────────────────────────

class MessageResponse(BaseModel):
    message: str
