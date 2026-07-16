"""
Session management endpoints: list sessions and revoke individual sessions.
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.audit import create_audit_log
from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.token import RefreshToken, Session
from app.models.user import User
from app.schemas.auth import MessageResponse, SessionRead

router = APIRouter()


@router.get("/", response_model=list[SessionRead], summary="List active sessions for current user")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Session]:
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id, Session.is_active == True)
        .order_by(Session.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{session_id}/revoke", response_model=MessageResponse,
             summary="Revoke a specific session")
async def revoke_session(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise NotFoundError("Session not found")

    if session.user_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenError("Cannot revoke another user's session")

    session.is_active = False

    # Revoke associated refresh tokens
    rt_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.session_id == session_id, RefreshToken.is_revoked == False
        )
    )
    for rt in rt_result.scalars().all():
        rt.is_revoked = True

    await create_audit_log(db, "session.revoked", "session", user_id=current_user.id,
                           resource_id=str(session_id), request=request)
    await db.commit()
    return MessageResponse(message="Session revoked successfully")
