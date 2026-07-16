"""
Redis client factory. Used for caching, rate limiting, and session/token
blocklists in later phases. Exposed as a FastAPI dependency (`get_redis`).
"""
from collections.abc import AsyncGenerator

import redis.asyncio as redis

from app.core.config import settings

_redis_pool: redis.ConnectionPool | None = None


def get_redis_pool() -> redis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.close()
