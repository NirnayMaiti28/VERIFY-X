from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import asyncio
import os
from text_verification.pipeline.verify_pipeline import VerificationPipeline

from slowapi import Limiter
from slowapi.util import get_remote_address

# Router
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

VERIFY_TIMEOUT_SECONDS = float(os.getenv("VERIFY_TIMEOUT_SECONDS", "45"))


# Request schema
class ClaimRequest(BaseModel):
    claim: str


# API endpoint
@router.post("/verify-text")
@limiter.limit("10/minute")
async def verify_text(request: Request, body: ClaimRequest):

    pipeline = getattr(request.app.state, "pipeline", None)
    pipeline_lock = getattr(request.app.state, "pipeline_lock", None)

    if pipeline is None or pipeline_lock is None:
        # Safety fallback if startup hook has not initialized state yet.
        if pipeline is None:
            request.app.state.pipeline = VerificationPipeline()
            pipeline = request.app.state.pipeline
        if pipeline_lock is None:
            request.app.state.pipeline_lock = asyncio.Lock()
            pipeline_lock = request.app.state.pipeline_lock

    try:
        async with pipeline_lock:
            result = await asyncio.wait_for(
                run_in_threadpool(pipeline.verify_claim, body.claim),
                timeout=VERIFY_TIMEOUT_SECONDS,
            )
    except asyncio.TimeoutError:
        result = {
            "claim": body.claim,
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "explanation": "Verification timed out before completing.",
            "evidence": [],
        }

    return result