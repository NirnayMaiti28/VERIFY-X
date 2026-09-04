"""
VERIFY-X 2.0 — Evidence detail endpoint.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_repository
from app.database.repositories import VerificationRepository
from app.schemas.evidence import EvidenceItem, EvidenceResponse

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/{request_id}", response_model=EvidenceResponse)
async def get_evidence(
    request_id: str,
    repo: VerificationRepository = Depends(get_repository),
) -> EvidenceResponse:
    """Get detailed evidence for a verification request."""
    try:
        req_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID format")

    request = await repo.get_verification_request(req_uuid)
    if not request:
        raise HTTPException(status_code=404, detail="Verification request not found")

    evidence_items = [
        EvidenceItem(
            evidence_id=e.evidence_id,
            source=e.url,
            title=e.title,
            url=e.url,
            published_at=e.published_at,
            passage=e.passage,
            relevance_score=e.relevance_score,
            stance=e.stance,
            language=e.language,
            retriever=e.retriever,
        )
        for e in request.evidence_items
    ]

    return EvidenceResponse(
        request_id=request_id,
        evidence=evidence_items,
        total_retrieved=len(evidence_items),
        total_selected=len(evidence_items),
    )
