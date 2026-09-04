"""
VERIFY-X 2.0 — Pydantic schemas for evidence.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EvidenceStance(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    NEUTRAL = "NEUTRAL"


class SourceTier(str, Enum):
    TIER_A = "A"  # Official/institutional sources
    TIER_B = "B"  # Established media
    TIER_C = "C"  # Unknown/blogs/unverified


class EvidenceItem(BaseModel):
    """A single piece of evidence used in verification."""
    evidence_id: str
    source: str
    title: str
    url: str
    published_at: datetime | None = None
    passage: str
    relevance_score: float = Field(ge=0, le=1)
    stance: EvidenceStance = EvidenceStance.NEUTRAL
    source_tier: SourceTier = SourceTier.TIER_C
    language: str = "en"
    retriever: str | None = None


class RetrievedDocument(BaseModel):
    """Raw document from a retrieval provider before ranking."""
    doc_id: str
    title: str
    url: str
    content: str
    source: str
    published_at: datetime | None = None
    language: str = "en"
    retriever: str = ""
    metadata: dict = Field(default_factory=dict)


class EvidenceResponse(BaseModel):
    """Response containing detailed evidence for a verification."""
    request_id: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    total_retrieved: int = 0
    total_selected: int = 0
