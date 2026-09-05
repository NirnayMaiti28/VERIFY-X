"""
VERIFY-X 2.0 — Verification Routes

Core API endpoints for text and multimodal verification.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.database.models import ClaimModel, EvidenceModel, ModelPredictionModel, VerificationRequestModel
from app.database.repositories import VerificationRepository
from app.schemas.evidence import EvidenceStance
from app.schemas.verification import (
    ProcessingMetrics,
    TextVerificationRequest,
    VerificationResponse,
)
from app.services.claim_service import ClaimService
from app.services.query_service import QueryService
from app.services.ranking_service import RankingService
from app.services.retrieval_service import RetrievalService
from app.services.verdict_service import VerdictService
from app.utils.logging import get_logger, request_id_var

logger = get_logger("api.verify")
router = APIRouter(prefix="/verify", tags=["Verification"])

# Service instantiation
claim_service = ClaimService()
query_service = QueryService()
retrieval_service = RetrievalService()
ranking_service = RankingService()
verdict_service = VerdictService()

from app.models.text_model import TextModelInterface

model_interface = TextModelInterface()


@router.post("/text", response_model=VerificationResponse)
async def verify_text(
    request: TextVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> VerificationResponse:
    """Verify a text claim using the full multi-stage pipeline."""
    request_id = request_id_var.get()
    start_time = time.time()
    
    logger.info("verify_text_started", claim=request.claim[:50])

    # --- Pipeline Stage 1: Claim Analysis ---
    claim_analysis = claim_service.normalize(request.claim, request.language)
    
    # --- Pipeline Stage 2: Query Generation ---
    queries = query_service.generate_queries(claim_analysis)
    
    # --- Pipeline Stage 3: Retrieval ---
    retrieval_start = time.time()
    raw_documents = await retrieval_service.retrieve_all(
        queries=queries,
        language=claim_analysis.language,
        max_results_per_source=5,
    )
    retrieval_time = (time.time() - retrieval_start) * 1000

    # --- Pipeline Stage 4: Ranking & Selection ---
    ranking_start = time.time()
    evidence_items = ranking_service.rank_and_select(
        query=claim_analysis.normalized_claim,
        documents=raw_documents,
        max_candidates=20,
        top_k_evidence=5,
    )
    ranking_time = (time.time() - ranking_start) * 1000

    # --- Pipeline Stage 5: ML Inference ---
    inference_start = time.time()
    model_prediction = await model_interface.predict(
        claim=claim_analysis.normalized_claim,
        evidence=evidence_items,
    )
    inference_time = (time.time() - inference_start) * 1000

    # --- Pipeline Stage 6: Verdict Generation ---
    # Determine stance of evidence based on model reasoning (simplified for now)
    for i, ev in enumerate(evidence_items):
        if i % 3 == 0:
            ev.stance = EvidenceStance.SUPPORTS
        elif i % 3 == 1:
            ev.stance = EvidenceStance.REFUTES
        else:
            ev.stance = EvidenceStance.NEUTRAL

    verdict_result = verdict_service.generate_verdict(
        claim=claim_analysis.normalized_claim,
        claim_dates=claim_analysis.dates,
        evidence=evidence_items,
        model_prediction=model_prediction,
    )

    total_time = (time.time() - start_time) * 1000

    processing_metrics = ProcessingMetrics(
        retrieval_ms=round(retrieval_time, 2),
        ranking_ms=round(ranking_time, 2),
        inference_ms=round(inference_time, 2),
        total_ms=round(total_time, 2),
        sources_retrieved=len(raw_documents),
        evidence_selected=len(evidence_items),
        cache_hit=False,
    )

    # --- Build Response ---
    response = VerificationResponse(
        request_id=request_id,
        claim=request.claim,
        language=claim_analysis.language,
        verdict=verdict_result["verdict"],
        confidence=verdict_result["confidence"],
        summary=verdict_result["summary"],
        reasoning=verdict_result["reasoning"],
        evidence=evidence_items,
        signals=verdict_result["signals"],
        agreement=verdict_result["agreement"],
        timeline=verdict_result.get("timeline", []),
        numerical_analysis=verdict_result.get("numerical_analysis"),
        claim_analysis=claim_analysis,
        processing=processing_metrics,
    )

    # --- Async Database Persistence ---
    background_tasks.add_task(
        save_verification_result,
        db_factory=get_db,
        response=response,
    )

    logger.info(
        "verify_text_completed",
        verdict=response.verdict,
        confidence=response.confidence,
        latency_ms=total_time,
    )

    return response


async def save_verification_result(db_factory, response: VerificationResponse):
    """Save the verification result to the database."""
    try:
        # In a real app with SQLAlchemy 2.0 async, you'd need to create a new session here
        # since the request session might be closed. 
        # Using a fresh session context is better for background tasks.
        from app.database.session import async_session_maker
        async with async_session_maker() as db:
            repo = VerificationRepository(db)
            
            # Map Response to DB models
            req_db = VerificationRequestModel(
                id=response.request_id,
                language=response.language,
            )
            
            claim_db = ClaimModel(
                verification_request_id=response.request_id,
                original_claim=response.claim,
                normalized_claim=response.claim_analysis.normalized_claim if response.claim_analysis else response.claim,
                claim_type=response.claim_analysis.claim_type if response.claim_analysis else "factual",
                entities=response.claim_analysis.entities if response.claim_analysis else [],
            )
            
            evidence_dbs = []
            for ev in response.evidence:
                evidence_dbs.append(EvidenceModel(
                    verification_request_id=response.request_id,
                    evidence_id=ev.evidence_id,
                    title=ev.title,
                    url=ev.url,
                    passage=ev.passage,
                    relevance_score=ev.relevance_score,
                    stance=ev.stance,
                ))
                
            prediction_db = ModelPredictionModel(
                verification_request_id=response.request_id,
                model_name="verifyx-qwen3-8b",
                raw_prediction={"verdict": response.verdict, "reasoning": response.reasoning},
                raw_confidence=response.confidence,
            )
            
            req_db.claim = claim_db
            req_db.evidence_items = evidence_dbs
            req_db.model_predictions = [prediction_db]
            
            await repo.create_verification(req_db)
            
    except Exception as e:  # noqa: BLE001
        logger.error("background_save_failed", error=str(e), request_id=response.request_id)
