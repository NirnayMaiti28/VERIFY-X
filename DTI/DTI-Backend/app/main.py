from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
import structlog

from app.config import settings
from app.dependencies import init_pipeline, get_pipeline_status
from app.api.v1.router import api_router
from app.middleware.cors import add_cors_middleware
from app.middleware.logging_middleware import LoggingMiddleware
from app.utils.error_handlers import (
    validation_exception_handler,
    rate_limit_handler,
    global_exception_handler
)

logger = structlog.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DTI backend...")

    # Set transformer env vars before pipeline import
    import os
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("USE_TF", "0")

    await init_pipeline()

    status = get_pipeline_status()
    if status:
        logger.info("Pipeline initialized successfully")
    else:
        logger.warning("Pipeline failed to initialize — /verify will return 503")

    yield

    logger.info("Shutting down DTI backend")

# Initialize the FastAPI application
app = FastAPI(
    title="DTI News Verifier API",
    description="API for the AI-powered news headline verification system",
    version="1.0.0",
    lifespan=lifespan
)

# 1. Register Middleware (Order matters: CORS should generally be first)
add_cors_middleware(app)
app.add_middleware(LoggingMiddleware)

# 2. Register Error Handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 3. Mount Routers
app.include_router(api_router)

# 4. Entry point for running directly via Python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.RELOAD
    )