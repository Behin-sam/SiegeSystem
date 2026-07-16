"""
Pydantic schemas for Audit Logs.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    action: str
    resource: str
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    details: dict[str, Any] | None
    created_at: datetime
