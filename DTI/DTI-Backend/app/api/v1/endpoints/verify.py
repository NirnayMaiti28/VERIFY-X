import asyncio
import logging
from fastapi import APIRouter, Depends, Request, File, UploadFile, Form
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional

from app.config import settings
from app.models.requests import VerifyRequest
from app.models.responses import VerifyResponse, ImageVerificationResult
from app.dependencies import get_pipeline
from app.services.verification_service import run_verification
from app.services.image_service import get_image_detector

logger = logging.getLogger(__name__)
router = APIRouter()

# Setup rate limiter using the user's IP address
limiter = Limiter(key_func=get_remote_address)

@router.post("/verify", response_model=VerifyResponse)
@limiter.limit(settings.RATE_LIMIT)
async def verify_claim(
    request: Request,
    body: VerifyRequest,
    pipeline = Depends(get_pipeline)
):
    """
    Takes a news headline claim and passes it to the AI verification pipeline.
    """
    if not body.claim:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_claim", "detail": "Either 'claim' must be provided."}
        )
    
    if pipeline is None:
        return JSONResponse(
            status_code=503,
            content={"error": "service_unavailable", "detail": "Verification service is not ready yet."}
        )
        
    try:
        raw_result = await run_verification(body.claim)
        return VerifyResponse(**raw_result)
        
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"error": "verification_timeout", "detail": "Verification timed out. Try a shorter claim."}
        )
        
    except RuntimeError:
        return JSONResponse(
            status_code=500,
            content={"error": "pipeline_error", "detail": "Verification failed due to an internal error."}
        )

    except Exception as exc:
        logger.exception("verify_claim failed")
        return JSONResponse(
            status_code=500,
            content={"error": "response_mapping_error", "detail": "Result could not be processed."}
        )


@router.post("/verify-image", response_model=VerifyResponse)
@limiter.limit(settings.RATE_LIMIT)
async def verify_image(
    request: Request,
    file: UploadFile = File(...),
    claim: Optional[str] = Form(None)
):
    """
    Verify an image for manipulation/fakeness. Optionally include a text claim to verify alongside.
    
    Args:
        file: Image file (jpg, png, etc.)
        claim: Optional text claim to verify alongside the image
    """
    if not file.filename:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_file", "detail": "Image file is required."}
        )
    
    # Validate file extension
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    if file_ext not in valid_extensions:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_file_type", "detail": f"Unsupported image format. Use one of: {', '.join(valid_extensions)}"}
        )
    
    try:
        # Read image bytes
        image_bytes = await file.read()
        if not image_bytes:
            return JSONResponse(
                status_code=400,
                content={"error": "empty_file", "detail": "Image file is empty."}
            )
        
        # Run image detection
        detector = get_image_detector()
        image_result = detector.predict(image_bytes)
        
        # Convert to response model
        image_verification = ImageVerificationResult(**image_result)
        
        # If a text claim was also provided, verify it as well
        text_result = None
        if claim and claim.strip():
            text_result = await run_verification(claim)
            return VerifyResponse(
                claim=claim,
                verdict=text_result.get("verdict"),
                confidence=text_result.get("confidence"),
                summary=text_result.get("summary"),
                explanation=text_result.get("explanation"),
                image_result=image_verification
            )
        else:
            # Return only image verification result
            return VerifyResponse(
                image_result=image_verification
            )
    
    except Exception as exc:
        logger.exception("verify_image failed")
        return JSONResponse(
            status_code=500,
            content={"error": "image_verification_failed", "detail": f"Image analysis failed: {type(exc).__name__}"}
        )