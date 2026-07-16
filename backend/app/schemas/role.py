"""
Pydantic schemas for Roles and Permissions.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionCreate(BaseModel):
    name: str
    description: str | None = None


class PermissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime


class RoleCreate(BaseModel):
    name: str
    description: str | None = None


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    permissions: list[PermissionRead] = []
    created_at: datetime


class AssignRoleRequest(BaseModel):
    user_id: uuid.UUID
    role_name: str


class RevokeRoleRequest(BaseModel):
    user_id: uuid.UUID
    role_name: str


class AssignPermissionRequest(BaseModel):
    role_id: uuid.UUID
    permission_name: str
