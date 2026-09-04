"""
VERIFY-X 2.0 — Feedback Routes

Endpoints for user feedback on verification results.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.utils.logging import get_logger

logger = get_logger("api.feedback")
router = APIRouter(prefix="/feedback", tags=["Feedback"])


class FeedbackRequest(BaseModel):
    request_id: str
    is_correct: bool
    user_verdict: str | None = None
    comment: str | None = None


@router.post("")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Submit feedback for a verification result."""
    logger.info(
        "feedback_received", 
        request_id=feedback.request_id, 
        is_correct=feedback.is_correct
    )
    
    # Store feedback in database (placeholder for actual DB logic)
    feedback_id = str(uuid.uuid4())
    
    return {
        "feedback_id": feedback_id,
        "received": True,
        "message": "Thank you for your feedback."
    }
