"""
Health and readiness endpoints — used by Docker healthchecks and load balancers.
"""
from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.redis_client.client import get_redis

router = APIRouter()


@router.get("/live", summary="Liveness probe")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe (checks DB + Redis connectivity)")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis),
) -> dict:
    checks = {"database": "unknown", "redis": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unreachable"

    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unreachable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
