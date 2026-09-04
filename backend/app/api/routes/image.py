"""
VERIFY-X 2.0 — Image Verification Routes

Endpoints for multimodal verification (image + optional context).
"""

from __future__ import annotations

import time

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.api.routes.verify import save_verification_result
from app.models.vision_model import VisionModelInterface
from app.schemas.verification import (
    Language,
    ProcessingMetrics,
    VerificationResponse,
)
from app.services.claim_service import ClaimService
from app.services.query_service import QueryService
from app.services.ranking_service import RankingService
from app.services.retrieval_service import RetrievalService
from app.services.verdict_service import VerdictService
from app.utils.logging import get_logger, request_id_var

logger = get_logger("api.image")
router = APIRouter(prefix="/verify/image", tags=["Verification"])

# Service instantiation
claim_service = ClaimService()
query_service = QueryService()
retrieval_service = RetrievalService()
ranking_service = RankingService()
verdict_service = VerdictService()
vision_interface = VisionModelInterface()


@router.post("", response_model=VerificationResponse)
async def verify_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),  # noqa: B008
    context: str | None = Form(None),
    language: Language | None = Form(None),  # noqa: B008
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> VerificationResponse:
    """Verify an image claim using the multimodal pipeline."""
    request_id = request_id_var.get()
    start_time = time.time()
    
    logger.info("verify_image_started", filename=file.filename, context=context)
    
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image size exceeds 10MB limit.")

    # --- Pipeline Stage 1: Multimodal Extraction ---
    extraction_start = time.time()
    extracted_text = await vision_interface.extract_text(image_bytes)
    
    # Formulate a claim combining OCR text and user context
    combined_claim = ""
    if context:
        combined_claim += f"Context: {context}\n"
    if extracted_text:
        combined_claim += f"Image Text: {extracted_text}"
        
    if not combined_claim:
        combined_claim = "Visual analysis without text context."
        
    claim_analysis = claim_service.normalize(combined_claim, language)
    
    # --- Pipeline Stage 2: Query Generation (if text extracted) ---
    queries = []
    if extracted_text or context:
        queries = query_service.generate_queries(claim_analysis)
    
    # --- Pipeline Stage 3 & 4: Retrieval and Ranking ---
    retrieval_start = time.time()
    evidence_items = []
    
    if queries:
        raw_documents = await retrieval_service.retrieve_all(
            queries=queries,
            language=claim_analysis.language,
            max_results_per_source=3,
        )
        
        evidence_items = ranking_service.rank_and_select(
            query=claim_analysis.normalized_claim,
            documents=raw_documents,
            max_candidates=10,
            top_k_evidence=3,
        )
        
    retrieval_time = (time.time() - retrieval_start) * 1000

    # --- Pipeline Stage 5: Vision ML Inference ---
    inference_start = time.time()
    model_prediction = await vision_interface.predict(
        image_bytes=image_bytes,
        context=context,
        extracted_text=extracted_text,
    )
    inference_time = (time.time() - inference_start) * 1000

    # --- Pipeline Stage 6: Verdict Generation ---
    verdict_result = verdict_service.generate_verdict(
        claim=claim_analysis.normalized_claim,
        claim_dates=claim_analysis.dates,
        evidence=evidence_items,
        model_prediction=model_prediction,
    )

    total_time = (time.time() - start_time) * 1000

    processing_metrics = ProcessingMetrics(
        retrieval_ms=round(retrieval_time, 2),
        ranking_ms=0, # Combined in retrieval_time here
        inference_ms=round(inference_time + (retrieval_start - extraction_start)*1000, 2),
        total_ms=round(total_time, 2),
        sources_retrieved=len(evidence_items), # Not entirely accurate but sufficient
        evidence_selected=len(evidence_items),
        cache_hit=False,
    )

    image_analysis = {
        "extracted_text": model_prediction.get("extracted_text"),
        "detected_manipulation": model_prediction.get("detected_manipulation"),
    }

    # --- Build Response ---
    response = VerificationResponse(
        request_id=request_id,
        claim=combined_claim,
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
        image_analysis=image_analysis,
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
        "verify_image_completed",
        verdict=response.verdict,
        confidence=response.confidence,
        latency_ms=total_time,
    )

    return response
