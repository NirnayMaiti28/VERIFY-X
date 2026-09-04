"""
VERIFY-X 2.0 — FastAPI Application Entry Point

Multimodal AI Fact Verification & Evidence Intelligence Platform
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.session import close_db, init_db
from app.utils.logging import get_logger, request_id_var, setup_logging

import uuid

settings = get_settings()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──
    setup_logging()
    logger.info("starting_verifyx", version=settings.app_version, mode=settings.model_mode.value)

    # Initialize database tables (dev only — use Alembic in production)
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.warning("database_init_skipped", error=str(e))

    yield

    # ── Shutdown ──
    await close_db()
    logger.info("verifyx_shutdown")


app = FastAPI(
    title="VERIFY-X 2.0",
    description="Multimodal AI Fact Verification & Evidence Intelligence Platform",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID Middleware ──
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Inject a unique request_id into every request context."""
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


# ── Register Routers ──
from app.api.routes.health import router as health_router
from app.api.routes.verify import router as verify_router
from app.api.routes.image import router as image_router
from app.api.routes.evidence import router as evidence_router
from app.api.routes.history import router as history_router
from app.api.routes.feedback import router as feedback_router

API_PREFIX = "/api/v1"

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(verify_router, prefix=API_PREFIX)
app.include_router(image_router, prefix=API_PREFIX)
app.include_router(evidence_router, prefix=API_PREFIX)
app.include_router(history_router, prefix=API_PREFIX)
app.include_router(feedback_router, prefix=API_PREFIX)


# ── Root ──
@app.get("/")
async def root():
    return {
        "name": "VERIFY-X 2.0",
        "description": "Multimodal AI Fact Verification & Evidence Intelligence Platform",
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{API_PREFIX}/health",
    }
