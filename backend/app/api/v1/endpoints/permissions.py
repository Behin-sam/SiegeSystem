"""
Permissions management endpoints.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_superuser
from app.core.audit import create_audit_log
from app.core.exceptions import ConflictError
from app.db.session import get_db
from app.models.role import Permission
from app.models.user import User
from app.schemas.role import PermissionCreate, PermissionRead

router = APIRouter()


@router.get("/", response_model=list[PermissionRead], summary="List all permissions")
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
) -> list[Permission]:
    result = await db.execute(select(Permission).order_by(Permission.name))
    return list(result.scalars().all())


@router.post("/", response_model=PermissionRead, status_code=201,
             summary="Create a new permission (Super Admin)")
async def create_permission(
    payload: PermissionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Permission:
    existing = await db.execute(select(Permission).where(Permission.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"Permission '{payload.name}' already exists")

    perm = Permission(name=payload.name, description=payload.description)
    db.add(perm)
    await create_audit_log(db, "permission.created", "permission", user_id=current_user.id,
                           request=request, details={"permission_name": payload.name})
    await db.commit()
    await db.refresh(perm)
    return perm
