"""
Utility for creating audit log entries consistently.
"""
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def create_audit_log(
    db: AsyncSession,
    action: str,
    resource: str,
    user_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Create an audit log entry. Call this inside any route/service
    that modifies sensitive data.
    """
    ip_address = None
    user_agent = None

    if request is not None:
        if request.client:
            ip_address = request.client.host
        user_agent = request.headers.get("user-agent")

    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        details=details,
    )
    db.add(log)
    # Do NOT commit here — caller controls the transaction
