"""
VERIFY-X 2.0 — FastAPI dependency injection.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.repositories import VerificationRepository
from app.database.session import get_db


async def get_redis(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AsyncGenerator[aioredis.Redis, None]:
    """Dependency that yields a Redis connection."""
    client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        yield client
    finally:
        await client.aclose()


async def get_repository(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> VerificationRepository:
    """Dependency that yields a VerificationRepository."""
    return VerificationRepository(db)
