from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Catches Pydantic 422 errors and formats them into our ErrorResponse schema."""
    errors = exc.errors()
    detail = "Validation error"
    
    if errors:
        # Grab the first error to keep the message simple for the frontend
        first_error = errors[0]
        field = ".".join(str(loc) for loc in first_error.get("loc", []) if loc != "body")
        msg = first_error.get("msg", "")
        detail = f"{field} {msg}".strip() if field else msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "detail": detail}
    )

async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Catches slowapi 429 errors and adds the retry_after field."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded", 
            "detail": f"{settings.RATE_LIMIT} allowed",
            "retry_after": 60 
        }
    )

async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catches any unhandled 500 errors so the server doesn't just drop the connection."""
    logger.error("unhandled_internal_server_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_error",
            "detail": "An unexpected server error occurred."
        }
    )