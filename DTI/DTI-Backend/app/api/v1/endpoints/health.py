from fastapi import APIRouter
from app.models.responses import HealthResponse
from app.dependencies import get_pipeline_status

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Checks if the server is running and if the AI pipeline successfully loaded.
    """
    return HealthResponse(
        status="ok",
        pipeline_ready=get_pipeline_status(),
        version="1.0.0"
    )