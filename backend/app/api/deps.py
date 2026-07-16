"""
Shared FastAPI dependencies for authentication, authorization (RBAC),
user status checks, and role/permission enforcement.
"""
import uuid
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if token is None:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Malformed token payload")

    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(user_id))
        .options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("User not found")

    if user.status == "disabled":
        raise ForbiddenError("Account has been disabled")

    if user.status == "suspended":
        raise ForbiddenError("Account is suspended")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return user


async def get_current_active_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser privileges required")
    return current_user


def has_role(*role_names: str) -> Callable:
    """Dependency factory that checks if the current user has at least one of the given roles."""
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role_names = {role.name for role in current_user.roles}
        if not user_role_names.intersection(set(role_names)):
            raise ForbiddenError(
                f"Access requires one of the following roles: {', '.join(role_names)}"
            )
        return current_user
    return _dependency


def has_permission(*permission_names: str) -> Callable:
    """Dependency factory that checks if the current user has at least one of the given permissions."""
    async def _dependency(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> User:
        from sqlalchemy.orm import selectinload as sload
        from app.models.role import Role

        # Reload user with roles and permissions
        result = await db.execute(
            select(User)
            .where(User.id == current_user.id)
            .options(
                sload(User.roles).selectinload(Role.permissions)
            )
        )
        user_full = result.scalar_one_or_none()
        if user_full is None:
            raise UnauthorizedError("User not found")

        user_permissions = set()
        for role in user_full.roles:
            for perm in role.permissions:
                user_permissions.add(perm.name)

        if not user_permissions.intersection(set(permission_names)):
            raise ForbiddenError(
                f"Access requires one of the following permissions: {', '.join(permission_names)}"
            )
        return current_user
    return _dependency


def get_request_meta(request: Request) -> dict:
    """Extract IP and user-agent from the request for audit logging."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
