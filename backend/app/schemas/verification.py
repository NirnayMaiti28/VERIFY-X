"""
VERIFY-X 2.0 — Pydantic schemas for verification requests and responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Verdict Labels ──

class VerdictEnum(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    PARTIALLY_TRUE = "PARTIALLY_TRUE"
    NOT_ENOUGH_INFORMATION = "NOT_ENOUGH_INFORMATION"


class ClaimType(str, Enum):
    FACTUAL = "factual"
    OPINION = "opinion"
    PREDICTION = "prediction"
    STATISTICAL = "statistical"
    HISTORICAL = "historical"
    SCIENTIFIC = "scientific"
    POLITICAL = "political"
    ECONOMIC = "economic"
    OTHER = "other"


class Language(str, Enum):
    ENGLISH = "en"
    HINDI = "hi"
    BENGALI = "bn"
    CODE_MIXED = "code-mixed"
    UNKNOWN = "unknown"


# ── Request Models ──

class TextVerificationRequest(BaseModel):
    """Request to verify a text claim."""
    claim: str = Field(..., min_length=5, max_length=2000, description="The claim to verify")
    language: Optional[Language] = Field(None, description="Language hint (auto-detected if not provided)")
    context: Optional[str] = Field(None, max_length=5000, description="Additional context for the claim")


# ── Signal Models ──

class VerificationSignals(BaseModel):
    """Individual verification signal scores."""
    model_confidence: float = Field(0.0, ge=0, le=1)
    evidence_relevance: float = Field(0.0, ge=0, le=1)
    source_credibility: float = Field(0.0, ge=0, le=1)
    agreement_score: float = Field(0.0, ge=0, le=1)
    temporal_consistency: float = Field(0.0, ge=0, le=1)
    numerical_consistency: float = Field(0.0, ge=0, le=1)


class NumericalAnalysis(BaseModel):
    """Results of numerical verification."""
    detected_numbers: list[dict[str, Any]] = Field(default_factory=list)
    calculations: list[dict[str, Any]] = Field(default_factory=list)
    consistency: Optional[float] = None


class TimelineEvent(BaseModel):
    """A point on the verification timeline."""
    date: str
    event: str
    source: Optional[str] = None
    relevance: Optional[str] = None


class ProcessingMetrics(BaseModel):
    """Latency and processing metrics."""
    retrieval_ms: int = 0
    ranking_ms: int = 0
    inference_ms: int = 0
    total_ms: int = 0
    sources_retrieved: int = 0
    evidence_selected: int = 0
    cache_hit: bool = False


class ClaimAnalysis(BaseModel):
    """Result of claim normalization and analysis."""
    original_claim: str
    normalized_claim: str
    entities: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    numbers: list[str] = Field(default_factory=list)
    claim_type: ClaimType = ClaimType.OTHER
    language: Language = Language.UNKNOWN


class SourceAgreement(BaseModel):
    """Cross-source agreement analysis."""
    support_count: int = 0
    refute_count: int = 0
    neutral_count: int = 0
    contradiction_strength: float = 0.0
    source_diversity: float = 0.0


# ── Response Models ──

class VerificationResponse(BaseModel):
    """Full verification result returned to the client."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim: str
    language: Language
    verdict: VerdictEnum
    confidence: float = Field(ge=0, le=1)
    summary: str
    reasoning: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    signals: VerificationSignals = Field(default_factory=VerificationSignals)
    agreement: SourceAgreement = Field(default_factory=SourceAgreement)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    numerical_analysis: Optional[NumericalAnalysis] = None
    image_analysis: Optional[dict[str, Any]] = None
    claim_analysis: Optional[ClaimAnalysis] = None
    processing: ProcessingMetrics = Field(default_factory=ProcessingMetrics)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VerificationSummary(BaseModel):
    """Lightweight verification result for history listings."""
    request_id: str
    claim: str
    verdict: VerdictEnum
    confidence: float
    language: Language
    evidence_count: int = 0
    created_at: datetime
