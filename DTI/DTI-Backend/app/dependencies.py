import os
import sys
import structlog
from typing import Optional, Any

# Add research package to Python path so backend can import text_verification.
_research_path = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "research", "research"
)
sys.path.insert(0, os.path.abspath(_research_path))

logger = structlog.get_logger(__name__)

# We use a try-except block for the import. 
# If the 'research' folder isn't on your local machine, the server still boots,
# setting pipeline_ready to False so the frontend knows the AI is down.
try:
    from text_verification.pipeline.verify_pipeline import VerificationPipeline
    MODEL_AVAILABLE = True
except ImportError:
    MODEL_AVAILABLE = False
    logger.warning("text_verification_module_not_found", detail="Running without AI model.")

# Module-level singletons
_pipeline: Optional[Any] = None
pipeline_ready: bool = False

async def init_pipeline() -> None:
    """
    Initializes the AI pipeline once at app startup.
    If it fails (e.g., missing API keys, or missing module), we catch the error 
    so the server doesn't crash, allowing the /health endpoint to report the failure.
    """
    global _pipeline, pipeline_ready
    
    if not MODEL_AVAILABLE:
        _pipeline = None
        pipeline_ready = False
        logger.error("pipeline_initialization_failed", error="text_verification module is missing from Python path")
        return

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        logger.info("initializing_pipeline")
        _pipeline = await loop.run_in_executor(
            None,
            VerificationPipeline
        )
        pipeline_ready = True
        logger.info("pipeline_initialized_successfully")
    except Exception as e:
        _pipeline = None
        pipeline_ready = False
        logger.error("pipeline_initialization_failed", error=str(e))

def get_pipeline() -> Optional[Any]:
    """
    FastAPI dependency to inject the pipeline into our routes.
    """
    return _pipeline


def get_pipeline_status() -> bool:
    return _pipeline is not None