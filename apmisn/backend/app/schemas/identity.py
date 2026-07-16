"""
Pydantic schemas for the Federated Identity module.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IdentitySignalCreate(BaseModel):
    signal_key: str
    signal_value: str
    confidence_delta: float = 0.0


class IdentitySignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signal_key: str
    signal_value: str
    confidence_delta: float
    created_at: datetime


class IdentityVerificationHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    verification_type: str
    status: str
    notes: str | None
    performed_by_user_id: uuid.UUID | None
    created_at: datetime


class IdentityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    region: str | None
    confidence_score: float
    verification_status: str
    signals: list[IdentitySignalRead] = []
    verification_history: list[IdentityVerificationHistoryRead] = []
    created_at: datetime
    updated_at: datetime


class IdentityUpdate(BaseModel):
    region: str | None = None


class VerifyIdentityRequest(BaseModel):
    verification_type: str  # e.g. "email", "mfa", "document"
    notes: str | None = None
