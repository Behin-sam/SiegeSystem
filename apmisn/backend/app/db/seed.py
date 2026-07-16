"""
Database seeding: creates default roles, permissions, and a super admin user on startup.
Safe to call repeatedly (idempotent).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.core.security import hash_password

logger = get_logger("apmisn.seed")

# ── Roles ──────────────────────────────────────────────────────────────
ROLES = [
    {"name": "Customer",              "description": "End-user customer"},
    {"name": "Merchant",              "description": "Business merchant"},
    {"name": "Bank",                  "description": "Banking institution representative"},
    {"name": "Settlement Authority",  "description": "Oversees settlement operations"},
    {"name": "Fraud Analyst",         "description": "Investigates fraud and risk signals"},
    {"name": "Compliance Officer",    "description": "Ensures regulatory compliance"},
    {"name": "Super Admin",           "description": "Full system access"},
]

# ── Permissions ────────────────────────────────────────────────────────
PERMISSIONS = [
    # Auth / users
    {"name": "user:read",            "description": "Read user data"},
    {"name": "user:write",           "description": "Create/update user data"},
    {"name": "user:delete",          "description": "Delete users"},
    {"name": "user:status",          "description": "Change user status (suspend/disable)"},
    # Roles / Permissions
    {"name": "role:read",            "description": "List roles and permissions"},
    {"name": "role:write",           "description": "Create/update roles and permissions"},
    {"name": "role:assign",          "description": "Assign roles to users"},
    # Identity
    {"name": "identity:read",        "description": "Read own identity"},
    {"name": "identity:read_any",    "description": "Read any user's identity"},
    {"name": "identity:write",       "description": "Update own identity"},
    {"name": "identity:verify",      "description": "Trigger verification workflow"},
    {"name": "identity:signal",      "description": "Add identity signals"},
    # Sessions / Audit
    {"name": "session:read",         "description": "Read sessions"},
    {"name": "session:revoke",       "description": "Revoke sessions"},
    {"name": "audit:read",           "description": "Read audit logs"},
]

# ── Role → Permissions mapping ─────────────────────────────────────────
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Customer": [
        "user:read", "identity:read", "identity:write",
        "session:read", "session:revoke",
    ],
    "Merchant": [
        "user:read", "identity:read", "identity:write",
        "session:read", "session:revoke",
    ],
    "Bank": [
        "user:read", "identity:read", "identity:read_any",
        "session:read",
    ],
    "Settlement Authority": [
        "user:read", "identity:read", "identity:read_any",
        "session:read", "audit:read",
    ],
    "Fraud Analyst": [
        "user:read", "identity:read", "identity:read_any",
        "identity:signal", "audit:read", "session:read",
    ],
    "Compliance Officer": [
        "user:read", "user:status", "identity:read", "identity:read_any",
        "identity:verify", "identity:signal",
        "audit:read", "session:read", "session:revoke",
    ],
    "Super Admin": [p["name"] for p in PERMISSIONS],  # all permissions
}

# ── Default super admin ────────────────────────────────────────────────
SUPER_ADMIN_EMAIL = "admin@apmisn.internal"
SUPER_ADMIN_PASSWORD = "SuperAdmin@123"


async def seed_roles_permissions(db: AsyncSession) -> None:
    from app.models.role import Permission, Role

    # Seed permissions
    perm_map: dict[str, Permission] = {}
    for pdata in PERMISSIONS:
        result = await db.execute(select(Permission).where(Permission.name == pdata["name"]))
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(**pdata)
            db.add(perm)
            await db.flush()
            logger.info("seeded_permission", name=perm.name)
        perm_map[perm.name] = perm

    # Seed roles and assign permissions
    for rdata in ROLES:
        result = await db.execute(
            select(Role).where(Role.name == rdata["name"]).options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name=rdata["name"], description=rdata["description"])
            db.add(role)
            await db.flush()
            logger.info("seeded_role", name=role.name)

        # Sync permissions
        existing_perm_names = {p.name for p in role.permissions}
        for perm_name in ROLE_PERMISSIONS.get(role.name, []):
            if perm_name not in existing_perm_names and perm_name in perm_map:
                role.permissions.append(perm_map[perm_name])

    await db.commit()
    logger.info("seed_complete", roles=len(ROLES), permissions=len(PERMISSIONS))


async def seed_super_admin(db: AsyncSession) -> None:
    from app.models.identity import Identity
    from app.models.mfa import MFA
    from app.models.role import Role
    from app.models.user import User

    result = await db.execute(select(User).where(User.email == SUPER_ADMIN_EMAIL))
    admin = result.scalar_one_or_none()

    if admin is None:
        admin = User(
            email=SUPER_ADMIN_EMAIL,
            hashed_password=hash_password(SUPER_ADMIN_PASSWORD),
            full_name="Super Admin",
            is_active=True,
            is_superuser=True,
            status="active",
            is_email_verified=True,
        )
        db.add(admin)
        await db.flush()

        # Attach Super Admin role
        role_result = await db.execute(select(Role).where(Role.name == "Super Admin"))
        sa_role = role_result.scalar_one_or_none()
        if sa_role:
            admin.roles.append(sa_role)

        # Create identity record
        identity = Identity(user_id=admin.id, confidence_score=1.0, verification_status="verified")
        db.add(identity)

        # Create MFA record (disabled)
        mfa = MFA(user_id=admin.id, is_enabled=False)
        db.add(mfa)

        await db.commit()
        logger.info("seeded_super_admin", email=SUPER_ADMIN_EMAIL)
    else:
        logger.info("super_admin_already_exists", email=SUPER_ADMIN_EMAIL)
