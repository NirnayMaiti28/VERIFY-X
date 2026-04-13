from fastapi import APIRouter
from app.api.v1.endpoints import verify, health

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(verify.router, tags=["Verification"])
api_router.include_router(health.router, tags=["System Status"])