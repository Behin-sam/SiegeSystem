"""
User profile, settings, activity logs, and management endpoints.
"""
import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_active_superuser, has_role
from app.core.audit import create_audit_log
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.user import AvatarUpdate, ProfileRead, ProfileUpdate, UserRead, UserStatusUpdate

router = APIRouter()

ALLOWED_STATUSES = {"active", "suspended", "disabled"}


@router.get("/profile", response_model=ProfileRead, summary="Get current user profile")
async def get_profile(current_user: User = Depends(get_current_user)) -> ProfileRead:
    return ProfileRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        is_email_verified=current_user.is_email_verified,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.put("/profile", response_model=ProfileRead, summary="Update current user profile")
async def update_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    await create_audit_log(db, "user.profile_updated", "user", user_id=current_user.id,
                           resource_id=str(current_user.id), request=request)
    await db.commit()
    await db.refresh(current_user)
    return ProfileRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        is_email_verified=current_user.is_email_verified,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.post("/profile/avatar", response_model=ProfileRead, summary="Update avatar URL (mock)")
async def update_avatar(
    payload: AvatarUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileRead:
    # Avatar support is mocked - store URL in audit log for now
    await create_audit_log(db, "user.avatar_updated", "user", user_id=current_user.id,
                           resource_id=str(current_user.id), request=request,
                           details={"avatar_url": payload.avatar_url})
    await db.commit()
    return ProfileRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        is_email_verified=current_user.is_email_verified,
        is_superuser=current_user.is_superuser,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )


@router.get("/activity-logs", response_model=list[AuditLogRead], summary="Get current user activity logs")
async def get_activity_logs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.get("/", response_model=list[UserRead], summary="List all users (Super Admin only)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
    limit: int = 50,
    offset: int = 0,
) -> list[User]:
    result = await db.execute(
        select(User).options(selectinload(User.roles))
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.get("/{user_id}", response_model=UserRead, summary="Get user by ID (Super Admin only)")
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")
    return user


@router.put("/{user_id}/status", response_model=UserRead, summary="Update user status (Admin/Compliance)")
async def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(has_role("Super Admin", "Compliance Officer")),
) -> User:
    if payload.status not in ALLOWED_STATUSES:
        raise ValidationError(f"Status must be one of: {', '.join(ALLOWED_STATUSES)}")

    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.roles))
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise NotFoundError("User not found")

    old_status = target.status
    target.status = payload.status
    target.is_active = payload.status == "active"

    await create_audit_log(db, "user.status_changed", "user", user_id=current_user.id,
                           resource_id=str(target.id), request=request,
                           details={"old_status": old_status, "new_status": payload.status})
    await db.commit()
    await db.refresh(target)
    return target
