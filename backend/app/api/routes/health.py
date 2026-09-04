"""
VERIFY-X 2.0 — Health Routes

Health check and system status endpoints.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    text_model: str
    vision_model: str
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint."""
    settings = get_settings()
    
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        database="connected",  # Mocked for now
        redis="connected",     # Mocked for now
        text_model=settings.model_mode.value,
        vision_model=settings.model_mode.value,
        timestamp=datetime.utcnow().isoformat(),
    )


class ModelInfoResponse(BaseModel):
    text_model: str
    text_adapter: Optional[str] = None
    vision_model: str
    vision_adapter: Optional[str] = None
    embedding_model: str
    model_mode: str

from typing import Optional

@router.get("/models", response_model=ModelInfoResponse)
async def model_info() -> ModelInfoResponse:
    """Get information about loaded models."""
    settings = get_settings()
    
    return ModelInfoResponse(
        text_model="Qwen/Qwen3-8B",
        vision_model="Qwen/Qwen2.5-VL-7B-Instruct",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        model_mode=settings.model_mode.value,
    )
