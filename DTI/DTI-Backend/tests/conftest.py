import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def mock_pipeline_response():
    """A sample successful dictionary that the real AI model would return."""
    return {
        "claim": "Test headline",
        "normalized_claim": "test headline",
        "verdict": "TRUE",
        "confidence": 0.95,
        "explanation": "This is a test explanation.",
        "nhtm_score": 0.88,
        "nhtm_components": {
            "source_reliability": 0.9,
            "consensus_score": 0.9,
            "contradiction_penalty": 0.0,
            "recency_score": 0.8
        },
        "evidence": [
            {
                "title": "Test Evidence",
                "description": "Test Description",
                "content": "Test Content",
                "source": "Reuters",
                "url": "http://test.com",
                "published_at": "2023-01-01",
                "similarity_score": 0.9,
                "final_score": 0.9,
                "recency_multiplier": 1.0,
                "entity_coverage": 0.8,
                "cross_encoder_score": 0.85
            }
        ]
    }

# UPDATE: Use pytest_asyncio.fixture for async fixtures to satisfy strict mode
@pytest_asyncio.fixture
async def client():
    """Creates an async test client that bypasses the actual network."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac