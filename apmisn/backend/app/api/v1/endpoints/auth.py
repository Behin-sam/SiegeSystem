"""
Full authentication endpoints: signup, login, logout, refresh (with rotation),
email verification, password change/reset, MFA setup and verification,
and session management.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_request_meta
from app.core.audit import create_audit_log
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from app.core.security import (
    create_access_token,
    create_email_verify_token,
    create_extended_refresh_token,
    create_mfa_challenge_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    generate_session_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.session import get_db
from app.models.identity import Identity
from app.models.mfa import MFA
from app.models.role import Role
from app.models.token import RefreshToken, Session
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    EmailVerifyRequest,
    LoginRequest,
    LogoutRequest,
    MFADisableRequest,
    MFAEnableRequest,
    MFARequiredResponse,
    MFASetupResponse,
    MFAVerifyLoginRequest,
    MessageResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    SignupRequest,
    SessionRead,
    TokenResponse,
)
from app.schemas.user import UserRead

router = APIRouter()


# ──────────────────────────────────────────────────────────────
# Signup
# ──────────────────────────────────────────────────────────────

@router.post("/signup", response_model=UserRead, status_code=201, summary="Register a new user")
async def signup(
    payload: SignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A user with this email already exists")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        status="active",
        is_email_verified=False,
    )
    db.add(user)
    await db.flush()

    # Assign default Customer role
    role_result = await db.execute(select(Role).where(Role.name == "Customer"))
    customer_role = role_result.scalar_one_or_none()
    if customer_role:
        user.roles.append(customer_role)

    # Create federated identity record
    identity = Identity(user_id=user.id, confidence_score=0.3, verification_status="unverified")
    db.add(identity)

    # Create MFA record (disabled by default)
    mfa = MFA(user_id=user.id, is_enabled=False)
    db.add(mfa)

    await create_audit_log(db, "auth.signup", "user", user_id=user.id,
                           resource_id=str(user.id), request=request)
    await db.commit()
    await db.refresh(user)
    return user


# ──────────────────────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────────────────────

@router.post("/login", summary="Exchange credentials for tokens")
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.email == payload.email).options(selectinload(User.mfa))
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Incorrect email or password")
    if user.status == "disabled":
        raise UnauthorizedError("Account has been disabled")
    if user.status == "suspended":
        raise UnauthorizedError("Account is suspended")
    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    # Create session
    session_token = generate_session_token()
    session_expiry = datetime.now(timezone.utc) + timedelta(
        days=30 if payload.remember_me else 1
    )
    session = Session(
        user_id=user.id,
        session_token=hash_token(session_token),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=session_expiry,
        is_active=True,
    )
    db.add(session)
    await db.flush()

    # Check MFA
    if user.mfa and user.mfa.is_enabled:
        mfa_token = create_mfa_challenge_token(str(user.id))
        await create_audit_log(db, "auth.login_mfa_required", "user", user_id=user.id,
                               request=request)
        await db.commit()
        return MFARequiredResponse(mfa_token=mfa_token)

    # Issue tokens
    access_token = create_access_token(str(user.id))
    if payload.remember_me:
        raw_refresh = create_extended_refresh_token(str(user.id))
    else:
        raw_refresh = create_refresh_token(str(user.id))

    refresh_payload = decode_token(raw_refresh)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        session_id=session.id,
        expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
    )
    db.add(rt)

    await create_audit_log(db, "auth.login", "user", user_id=user.id, request=request)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


# ──────────────────────────────────────────────────────────────
# Logout
# ──────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse, summary="Revoke session and refresh token")
async def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    token_hash = hash_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == current_user.id,
        )
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.is_revoked = True
        if rt.session_id:
            sess_result = await db.execute(select(Session).where(Session.id == rt.session_id))
            sess = sess_result.scalar_one_or_none()
            if sess:
                sess.is_active = False

    await create_audit_log(db, "auth.logout", "user", user_id=current_user.id, request=request)
    await db.commit()
    return MessageResponse(message="Logged out successfully")


# ──────────────────────────────────────────────────────────────
# Token Refresh (with Rotation)
# ──────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse, summary="Rotate refresh token")
async def refresh_token(
    payload: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    decoded = decode_token(payload.refresh_token)
    if decoded is None or decoded.get("type") != "refresh":
        raise UnauthorizedError("Invalid or expired refresh token")

    subject = decoded.get("sub")
    if not subject:
        raise UnauthorizedError("Malformed refresh token")

    token_hash = hash_token(payload.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()

    if rt is None:
        raise UnauthorizedError("Refresh token not found")

    if rt.is_revoked:
        raise UnauthorizedError("Refresh token has been revoked")

    # RTR: detect reuse — if already used, revoke all tokens for this user (security breach)
    if rt.is_used:
        all_tokens = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == rt.user_id, RefreshToken.is_revoked == False
            )
        )
        for old_rt in all_tokens.scalars().all():
            old_rt.is_revoked = True
        all_sessions = await db.execute(
            select(Session).where(Session.user_id == rt.user_id, Session.is_active == True)
        )
        for sess in all_sessions.scalars().all():
            sess.is_active = False
        await create_audit_log(db, "auth.refresh_token_reuse_detected", "user",
                               user_id=rt.user_id, request=request)
        await db.commit()
        raise UnauthorizedError("Refresh token reuse detected — all sessions revoked for security")

    # Mark old token as used
    rt.is_used = True

    # Issue new tokens
    new_access = create_access_token(subject)
    new_raw_refresh = create_refresh_token(subject)
    new_decoded = decode_token(new_raw_refresh)

    new_rt = RefreshToken(
        user_id=rt.user_id,
        token_hash=hash_token(new_raw_refresh),
        parent_id=rt.id,
        session_id=rt.session_id,
        expires_at=datetime.fromtimestamp(new_decoded["exp"], tz=timezone.utc),
    )
    db.add(new_rt)

    await create_audit_log(db, "auth.token_refresh", "user", user_id=rt.user_id, request=request)
    await db.commit()

    return TokenResponse(access_token=new_access, refresh_token=new_raw_refresh)


# ──────────────────────────────────────────────────────────────
# Change Password
# ──────────────────────────────────────────────────────────────

@router.post("/change-password", response_model=MessageResponse, summary="Change current password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise UnauthorizedError("Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    await create_audit_log(db, "auth.change_password", "user", user_id=current_user.id,
                           resource_id=str(current_user.id), request=request)
    await db.commit()
    return MessageResponse(message="Password changed successfully")


# ──────────────────────────────────────────────────────────────
# Password Reset
# ──────────────────────────────────────────────────────────────

@router.post("/reset-password/request", response_model=MessageResponse,
             summary="Request password reset token")
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    # Always return success to avoid email enumeration
    if user:
        token = create_password_reset_token(str(user.id))
        # In production, this would be emailed. Here we log it.
        await create_audit_log(db, "auth.password_reset_requested", "user", user_id=user.id,
                               request=request, details={"mock_token": token})
        await db.commit()
    return MessageResponse(message="If the email exists, a password reset link has been sent")


@router.post("/reset-password/confirm", response_model=MessageResponse,
             summary="Confirm password reset with token")
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    decoded = decode_token(payload.token)
    if decoded is None or decoded.get("type") != "password_reset":
        raise UnauthorizedError("Invalid or expired password reset token")

    user_id = decoded.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    user.hashed_password = hash_password(payload.new_password)
    await create_audit_log(db, "auth.password_reset_confirmed", "user", user_id=user.id,
                           request=request)
    await db.commit()
    return MessageResponse(message="Password has been reset successfully")


# ──────────────────────────────────────────────────────────────
# Email Verification
# ──────────────────────────────────────────────────────────────

@router.post("/email-verification/request", response_model=MessageResponse,
             summary="Request email verification token (mock)")
async def request_email_verification(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    token = create_email_verify_token(str(current_user.id))
    await create_audit_log(db, "auth.email_verification_requested", "user",
                           user_id=current_user.id, request=request,
                           details={"mock_token": token})
    await db.commit()
    return MessageResponse(message=f"[MOCK] Email verification token: {token}")


@router.post("/email-verification/verify", response_model=MessageResponse,
             summary="Verify email address using token")
async def verify_email(
    payload: EmailVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    decoded = decode_token(payload.token)
    if decoded is None or decoded.get("type") != "email_verify":
        raise UnauthorizedError("Invalid or expired email verification token")

    user_id = decoded.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    user.is_email_verified = True

    # Add identity signal for email verification
    id_result = await db.execute(select(Identity).where(Identity.user_id == user.id))
    identity = id_result.scalar_one_or_none()
    if identity:
        from app.models.identity import IdentitySignal, IdentityVerificationHistory
        signal = IdentitySignal(
            identity_id=identity.id,
            signal_key="email_verified",
            signal_value="true",
            confidence_delta=0.2,
        )
        db.add(signal)
        identity.confidence_score = min(1.0, identity.confidence_score + 0.2)

        hist = IdentityVerificationHistory(
            identity_id=identity.id,
            verification_type="email",
            status="success",
            notes="Email verified via token",
        )
        db.add(hist)

    await create_audit_log(db, "auth.email_verified", "user", user_id=user.id, request=request)
    await db.commit()
    return MessageResponse(message="Email verified successfully")


# ──────────────────────────────────────────────────────────────
# MFA
# ──────────────────────────────────────────────────────────────

@router.post("/mfa/setup", response_model=MFASetupResponse, summary="Set up MFA (generates mock secret)")
async def mfa_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MFASetupResponse:
    result = await db.execute(select(MFA).where(MFA.user_id == current_user.id))
    mfa = result.scalar_one_or_none()
    mock_secret = f"MOCK-SECRET-{current_user.id}"
    if mfa is None:
        mfa = MFA(user_id=current_user.id, secret=mock_secret, is_enabled=False)
        db.add(mfa)
    else:
        mfa.secret = mock_secret
    await db.commit()
    return MFASetupResponse(
        secret=mock_secret,
        message=f"[MOCK] Scan this secret in your authenticator app. Use code '{settings.MFA_OTP_CODE}' to verify.",
    )


@router.post("/mfa/enable", response_model=MessageResponse, summary="Enable MFA after verifying code")
async def mfa_enable(
    payload: MFAEnableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if payload.code != settings.MFA_OTP_CODE:
        raise UnauthorizedError("Invalid MFA code")

    result = await db.execute(select(MFA).where(MFA.user_id == current_user.id))
    mfa = result.scalar_one_or_none()
    if mfa is None:
        raise NotFoundError("MFA not set up — call /auth/mfa/setup first")
    mfa.is_enabled = True

    # Add identity signal
    id_result = await db.execute(select(Identity).where(Identity.user_id == current_user.id))
    identity = id_result.scalar_one_or_none()
    if identity:
        from app.models.identity import IdentitySignal
        signal = IdentitySignal(
            identity_id=identity.id, signal_key="mfa_enabled",
            signal_value="true", confidence_delta=0.2,
        )
        db.add(signal)
        identity.confidence_score = min(1.0, identity.confidence_score + 0.2)

    await create_audit_log(db, "auth.mfa_enabled", "user", user_id=current_user.id, request=request)
    await db.commit()
    return MessageResponse(message="MFA enabled successfully")


@router.post("/mfa/disable", response_model=MessageResponse, summary="Disable MFA")
async def mfa_disable(
    payload: MFADisableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    if payload.code != settings.MFA_OTP_CODE:
        raise UnauthorizedError("Invalid MFA code")

    result = await db.execute(select(MFA).where(MFA.user_id == current_user.id))
    mfa = result.scalar_one_or_none()
    if mfa is None or not mfa.is_enabled:
        raise NotFoundError("MFA is not enabled for this account")
    mfa.is_enabled = False

    await create_audit_log(db, "auth.mfa_disabled", "user", user_id=current_user.id, request=request)
    await db.commit()
    return MessageResponse(message="MFA disabled successfully")


@router.post("/mfa/verify-login", response_model=TokenResponse,
             summary="Complete MFA login with OTP code")
async def mfa_verify_login(
    payload: MFAVerifyLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    decoded = decode_token(payload.mfa_token)
    if decoded is None or decoded.get("type") != "mfa_challenge":
        raise UnauthorizedError("Invalid or expired MFA challenge token")

    if payload.code != settings.MFA_OTP_CODE:
        raise UnauthorizedError("Invalid MFA code")

    user_id = decoded.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError("User not found")

    access_token = create_access_token(str(user.id))
    raw_refresh = create_refresh_token(str(user.id))
    refresh_decoded = decode_token(raw_refresh)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=datetime.fromtimestamp(refresh_decoded["exp"], tz=timezone.utc),
    )
    db.add(rt)

    await create_audit_log(db, "auth.mfa_verified", "user", user_id=user.id, request=request)
    await db.commit()

    return TokenResponse(access_token=access_token, refresh_token=raw_refresh)


# ──────────────────────────────────────────────────────────────
# Me
# ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserRead, summary="Get the currently authenticated user")
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
