"""
Federated Identity endpoints: retrieve, update, verify, add signals, and get history.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, has_role
from app.core.audit import create_audit_log
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.identity import Identity, IdentitySignal, IdentityVerificationHistory
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.identity import (
    IdentityRead,
    IdentitySignalCreate,
    IdentitySignalRead,
    IdentityUpdate,
    IdentityVerificationHistoryRead,
    VerifyIdentityRequest,
)

router = APIRouter()

PRIVILEGED_ROLES = ("Bank", "Fraud Analyst", "Compliance Officer", "Super Admin", "Settlement Authority")


async def _get_identity_with_details(db: AsyncSession, user_id: uuid.UUID) -> Identity:
    result = await db.execute(
        select(Identity)
        .where(Identity.user_id == user_id)
        .options(
            selectinload(Identity.signals),
            selectinload(Identity.verification_history),
        )
    )
    identity = result.scalar_one_or_none()
    if identity is None:
        raise NotFoundError("Identity record not found")
    return identity


@router.get("/me", response_model=IdentityRead, summary="Get current user's identity")
async def get_my_identity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Identity:
    return await _get_identity_with_details(db, current_user.id)


@router.put("/me", response_model=IdentityRead, summary="Update current user's identity (region)")
async def update_my_identity(
    payload: IdentityUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Identity:
    identity = await _get_identity_with_details(db, current_user.id)
    if payload.region is not None:
        identity.region = payload.region
    await create_audit_log(db, "identity.updated", "identity", user_id=current_user.id,
                           resource_id=str(identity.id), request=request)
    await db.commit()
    await db.refresh(identity)
    return identity


@router.get("/{user_id}", response_model=IdentityRead,
            summary="Get identity by user ID (privileged roles only)")
async def get_identity_by_user(
    user_id: uuid.UUID,
    current_user: User = Depends(has_role(*PRIVILEGED_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> Identity:
    return await _get_identity_with_details(db, user_id)


@router.post("/{user_id}/verify", response_model=IdentityRead,
             summary="Trigger verification workflow (Compliance, Super Admin)")
async def verify_identity(
    user_id: uuid.UUID,
    payload: VerifyIdentityRequest,
    request: Request,
    current_user: User = Depends(has_role("Compliance Officer", "Super Admin")),
    db: AsyncSession = Depends(get_db),
) -> Identity:
    identity = await _get_identity_with_details(db, user_id)

    # Run mock verification — always succeeds
    identity.verification_status = "verified"
    identity.confidence_score = min(1.0, identity.confidence_score + 0.15)

    hist = IdentityVerificationHistory(
        identity_id=identity.id,
        verification_type=payload.verification_type,
        status="success",
        notes=payload.notes or f"Verified by {current_user.email}",
        performed_by_user_id=current_user.id,
    )
    db.add(hist)

    await create_audit_log(db, "identity.verified", "identity", user_id=current_user.id,
                           resource_id=str(identity.id), request=request,
                           details={"verification_type": payload.verification_type})
    await db.commit()
    await db.refresh(identity)
    return identity


@router.post("/{user_id}/signals", response_model=IdentityRead,
             summary="Add identity signal (Fraud Analyst, Compliance, Super Admin)")
async def add_identity_signal(
    user_id: uuid.UUID,
    payload: IdentitySignalCreate,
    request: Request,
    current_user: User = Depends(has_role("Fraud Analyst", "Compliance Officer", "Super Admin")),
    db: AsyncSession = Depends(get_db),
) -> Identity:
    identity = await _get_identity_with_details(db, user_id)

    signal = IdentitySignal(
        identity_id=identity.id,
        signal_key=payload.signal_key,
        signal_value=payload.signal_value,
        confidence_delta=payload.confidence_delta,
    )
    db.add(signal)

    # Recalibrate confidence score
    identity.confidence_score = max(0.0, min(1.0, identity.confidence_score + payload.confidence_delta))

    # Log verification history for signal addition
    hist = IdentityVerificationHistory(
        identity_id=identity.id,
        verification_type="signal",
        status="success",
        notes=f"Signal '{payload.signal_key}' added by {current_user.email}",
        performed_by_user_id=current_user.id,
    )
    db.add(hist)

    await create_audit_log(db, "identity.signal_added", "identity", user_id=current_user.id,
                           resource_id=str(identity.id), request=request,
                           details={"signal_key": payload.signal_key, "delta": payload.confidence_delta})
    await db.commit()
    await db.refresh(identity)
    return identity


@router.get("/{user_id}/history", response_model=list[IdentityVerificationHistoryRead],
            summary="Get identity verification history (privileged roles only)")
async def get_verification_history(
    user_id: uuid.UUID,
    current_user: User = Depends(has_role(*PRIVILEGED_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> list[IdentityVerificationHistory]:
    id_result = await db.execute(select(Identity).where(Identity.user_id == user_id))
    identity = id_result.scalar_one_or_none()
    if identity is None:
        raise NotFoundError("Identity not found")

    hist_result = await db.execute(
        select(IdentityVerificationHistory)
        .where(IdentityVerificationHistory.identity_id == identity.id)
        .order_by(IdentityVerificationHistory.created_at.desc())
    )
    return list(hist_result.scalars().all())
