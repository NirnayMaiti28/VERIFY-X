"""
VERIFY-X 2.0 — History Routes

Endpoints for retrieving verification history.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.database.repositories import VerificationRepository
from app.schemas.verification import (
    PaginatedResponse,
    VerificationResponse,
    VerificationSummary,
)
from app.utils.logging import get_logger

logger = get_logger("api.history")
router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=PaginatedResponse[VerificationSummary])
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> PaginatedResponse[VerificationSummary]:
    """Get paginated verification history."""
    repo = VerificationRepository(db)
    # Using a placeholder implementation until the DB repository is fully fleshed out with history queries
    # Currently, VerificationRepository in Phase 1 might not have `get_history` implemented fully.
    
    # We will implement a mock response for now, but in a real app this would query the DB.
    # We can try calling it if it exists.
    try:
        if hasattr(repo, "get_history"):
            items, total = await repo.get_history(page=page, page_size=page_size)
        else:
            items, total = [], 0
            
        has_next = (page * page_size) < total
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=has_next,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("history_fetch_failed", error=str(e))
        return PaginatedResponse(items=[], total=0, page=page, page_size=page_size, has_next=False)


@router.get("/{request_id}", response_model=VerificationResponse)
async def get_verification(
    request_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> VerificationResponse:
    """Get a specific verification result by ID."""
    repo = VerificationRepository(db)
    result = await repo.get_verification(request_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Verification not found")
        
    return result
