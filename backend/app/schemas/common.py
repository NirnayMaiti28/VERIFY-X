"""
VERIFY-X 2.0 — Common/shared Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str | None = None
    request_id: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = ""
    database: str = "unknown"
    redis: str = "unknown"
    text_model: str = "not_loaded"
    vision_model: str = "not_loaded"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    has_next: bool = False


class FeedbackRequest(BaseModel):
    """User feedback on a verification result."""
    request_id: str
    is_correct: bool
    user_verdict: str | None = None
    comment: str | None = Field(None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    feedback_id: str
    request_id: str
    received: bool = True
    message: str = "Thank you for your feedback."


class ModelInfoResponse(BaseModel):
    """Information about loaded models."""
    text_model: str = ""
    text_adapter: str | None = None
    vision_model: str = ""
    vision_adapter: str | None = None
    embedding_model: str = ""
    model_mode: str = "local"
