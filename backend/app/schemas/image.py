"""
VERIFY-X 2.0 — Pydantic schemas for image verification.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImageVerificationRequest(BaseModel):
    """Request to verify an image (file upload handled separately)."""
    context: str | None = Field(None, max_length=2000, description="Additional context")
    language: str | None = Field(None, description="Language hint")


class ImageAnalysisResult(BaseModel):
    """Result of image analysis pipeline."""
    detected_text: str = ""
    claim: str = ""
    visual_description: str = ""
    entities: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    ocr_confidence: float = 0.0
    vlm_confidence: float = 0.0
    ocr_vlm_agreement: bool = True
    discrepancy_notes: str | None = None


class ImageAuthenticitySignal(BaseModel):
    """Image authenticity analysis result."""
    has_exif: bool = False
    compression_artifacts: str | None = None
    manipulation_indicators: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    assessment: str = "UNKNOWN"
    notes: str = ""
