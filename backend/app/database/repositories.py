"""
VERIFY-X 2.0 — Repository pattern for database operations.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    ClaimModel,
    EvidenceModel,
    FeedbackModel,
    ModelPredictionModel,
    SourceModel,
    VerdictModel,
    VerificationRequestModel,
)


class VerificationRepository:
    """CRUD operations for verification requests and related entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Verification Requests ──

    async def create_verification_request(
        self,
        original_input: str,
        request_type: str = "text",
        language: str = "unknown",
    ) -> VerificationRequestModel:
        request = VerificationRequestModel(
            original_input=original_input,
            request_type=request_type,
            language=language,
            status="pending",
        )
        self.db.add(request)
        await self.db.flush()
        return request

    async def get_verification_request(
        self, request_id: uuid.UUID
    ) -> VerificationRequestModel | None:
        result = await self.db.execute(
            select(VerificationRequestModel)
            .options(
                selectinload(VerificationRequestModel.claim),
                selectinload(VerificationRequestModel.verdict),
                selectinload(VerificationRequestModel.evidence_items),
            )
            .where(VerificationRequestModel.id == request_id)
        )
        return result.scalar_one_or_none()

    async def update_verification_status(
        self, request_id: uuid.UUID, status: str, processing_ms: int = 0
    ) -> None:
        result = await self.db.execute(
            select(VerificationRequestModel).where(
                VerificationRequestModel.id == request_id
            )
        )
        request = result.scalar_one_or_none()
        if request:
            request.status = status
            request.processing_ms = processing_ms

    async def list_verification_requests(
        self, page: int = 1, page_size: int = 20
    ) -> tuple[list[VerificationRequestModel], int]:
        # Count total
        count_result = await self.db.execute(
            select(VerificationRequestModel.id)
        )
        total = len(count_result.all())

        # Fetch page
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(VerificationRequestModel)
            .options(
                selectinload(VerificationRequestModel.verdict),
            )
            .order_by(desc(VerificationRequestModel.created_at))
            .offset(offset)
            .limit(page_size)
        )
        items = list(result.scalars().all())
        return items, total

    # ── Claims ──

    async def create_claim(
        self,
        verification_request_id: uuid.UUID,
        original_claim: str,
        normalized_claim: str,
        claim_hash: str,
        claim_type: str = "other",
        entities: list | None = None,
        dates: list | None = None,
        locations: list | None = None,
        numbers: list | None = None,
        language: str = "unknown",
    ) -> ClaimModel:
        claim = ClaimModel(
            verification_request_id=verification_request_id,
            original_claim=original_claim,
            normalized_claim=normalized_claim,
            claim_hash=claim_hash,
            claim_type=claim_type,
            entities=entities or [],
            dates=dates or [],
            locations=locations or [],
            numbers=numbers or [],
            language=language,
        )
        self.db.add(claim)
        await self.db.flush()
        return claim

    async def find_claim_by_hash(self, claim_hash: str) -> ClaimModel | None:
        result = await self.db.execute(
            select(ClaimModel).where(ClaimModel.claim_hash == claim_hash)
        )
        return result.scalar_one_or_none()

    # ── Evidence ──

    async def create_evidence(
        self,
        verification_request_id: uuid.UUID,
        evidence_id: str,
        title: str,
        url: str,
        passage: str,
        relevance_score: float,
        stance: str = "NEUTRAL",
        source_id: uuid.UUID | None = None,
        published_at: datetime | None = None,
        retriever: str = "",
        language: str = "en",
    ) -> EvidenceModel:
        evidence = EvidenceModel(
            verification_request_id=verification_request_id,
            evidence_id=evidence_id,
            source_id=source_id,
            title=title,
            url=url,
            passage=passage,
            published_at=published_at,
            relevance_score=relevance_score,
            stance=stance,
            retriever=retriever,
            language=language,
        )
        self.db.add(evidence)
        await self.db.flush()
        return evidence

    # ── Sources ──

    async def get_or_create_source(
        self, domain: str, name: str = "", tier: str = "C", category: str = "unknown"
    ) -> SourceModel:
        result = await self.db.execute(
            select(SourceModel).where(SourceModel.domain == domain)
        )
        source = result.scalar_one_or_none()
        if source:
            return source

        source = SourceModel(
            domain=domain,
            name=name or domain,
            tier=tier,
            category=category,
        )
        self.db.add(source)
        await self.db.flush()
        return source

    # ── Verdicts ──

    async def create_verdict(
        self,
        verification_request_id: uuid.UUID,
        verdict: str,
        confidence: float,
        summary: str,
        reasoning: str,
        signals: dict | None = None,
        agreement: dict | None = None,
        timeline: list | None = None,
        numerical_analysis: dict | None = None,
        image_analysis: dict | None = None,
    ) -> VerdictModel:
        verdict_model = VerdictModel(
            verification_request_id=verification_request_id,
            verdict=verdict,
            confidence=confidence,
            summary=summary,
            reasoning=reasoning,
            signals=signals or {},
            agreement=agreement or {},
            timeline=timeline or [],
            numerical_analysis=numerical_analysis,
            image_analysis=image_analysis,
        )
        self.db.add(verdict_model)
        await self.db.flush()
        return verdict_model

    # ── Model Predictions ──

    async def create_model_prediction(
        self,
        verification_request_id: uuid.UUID,
        model_name: str,
        raw_prediction: dict,
        raw_confidence: float,
        model_version: str = "",
        calibrated_confidence: float | None = None,
        latency_ms: int = 0,
    ) -> ModelPredictionModel:
        prediction = ModelPredictionModel(
            verification_request_id=verification_request_id,
            model_name=model_name,
            model_version=model_version,
            raw_prediction=raw_prediction,
            raw_confidence=raw_confidence,
            calibrated_confidence=calibrated_confidence,
            latency_ms=latency_ms,
        )
        self.db.add(prediction)
        await self.db.flush()
        return prediction

    # ── Feedback ──

    async def create_feedback(
        self,
        verification_request_id: uuid.UUID,
        is_correct: bool,
        user_verdict: str | None = None,
        comment: str | None = None,
    ) -> FeedbackModel:
        feedback = FeedbackModel(
            verification_request_id=verification_request_id,
            is_correct=is_correct,
            user_verdict=user_verdict,
            comment=comment,
        )
        self.db.add(feedback)
        await self.db.flush()
        return feedback
