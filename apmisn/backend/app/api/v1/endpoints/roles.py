"""
Roles and RBAC endpoints: create roles, list roles, assign roles to users,
and manage role permissions.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_superuser
from app.core.audit import create_audit_log
from app.core.exceptions import ConflictError, NotFoundError
from app.db.session import get_db
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.role import AssignPermissionRequest, AssignRoleRequest, RoleCreate, RoleRead, RevokeRoleRequest

router = APIRouter()


@router.get("/", response_model=list[RoleRead], summary="List all roles")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_superuser),
) -> list[Role]:
    result = await db.execute(
        select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
    )
    return list(result.scalars().all())


@router.post("/", response_model=RoleRead, status_code=201, summary="Create a new role (Super Admin)")
async def create_role(
    payload: RoleCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> Role:
    existing = await db.execute(select(Role).where(Role.name == payload.name))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"Role '{payload.name}' already exists")

    role = Role(name=payload.name, description=payload.description)
    db.add(role)
    await create_audit_log(db, "role.created", "role", user_id=current_user.id,
                           request=request, details={"role_name": payload.name})
    await db.commit()
    await db.refresh(role)
    return role


@router.post("/assign", response_model=MessageResponse, summary="Assign a role to a user")
async def assign_role(
    payload: AssignRoleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> MessageResponse:
    user_result = await db.execute(
        select(User).where(User.id == payload.user_id).options(selectinload(User.roles))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    role_result = await db.execute(select(Role).where(Role.name == payload.role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise NotFoundError(f"Role '{payload.role_name}' not found")

    if role in user.roles:
        return MessageResponse(message=f"User already has role '{payload.role_name}'")

    user.roles.append(role)
    await create_audit_log(db, "role.assigned", "user", user_id=current_user.id,
                           resource_id=str(payload.user_id), request=request,
                           details={"role_name": payload.role_name})
    await db.commit()
    return MessageResponse(message=f"Role '{payload.role_name}' assigned to user")


@router.post("/revoke", response_model=MessageResponse, summary="Revoke a role from a user")
async def revoke_role(
    payload: RevokeRoleRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> MessageResponse:
    user_result = await db.execute(
        select(User).where(User.id == payload.user_id).options(selectinload(User.roles))
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    role_result = await db.execute(select(Role).where(Role.name == payload.role_name))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise NotFoundError(f"Role '{payload.role_name}' not found")

    if role not in user.roles:
        return MessageResponse(message=f"User does not have role '{payload.role_name}'")

    user.roles.remove(role)
    await create_audit_log(db, "role.revoked", "user", user_id=current_user.id,
                           resource_id=str(payload.user_id), request=request,
                           details={"role_name": payload.role_name})
    await db.commit()
    return MessageResponse(message=f"Role '{payload.role_name}' revoked from user")


@router.post("/{role_id}/permissions", response_model=MessageResponse,
             summary="Assign a permission to a role")
async def assign_permission_to_role(
    role_id: uuid.UUID,
    payload: AssignPermissionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
) -> MessageResponse:
    role_result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = role_result.scalar_one_or_none()
    if role is None:
        raise NotFoundError("Role not found")

    perm_result = await db.execute(select(Permission).where(Permission.name == payload.permission_name))
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        raise NotFoundError(f"Permission '{payload.permission_name}' not found")

    if perm in role.permissions:
        return MessageResponse(message=f"Role already has permission '{payload.permission_name}'")

    role.permissions.append(perm)
    await create_audit_log(db, "role.permission_assigned", "role", user_id=current_user.id,
                           resource_id=str(role_id), request=request,
                           details={"permission_name": payload.permission_name})
    await db.commit()
    return MessageResponse(message=f"Permission '{payload.permission_name}' assigned to role")
