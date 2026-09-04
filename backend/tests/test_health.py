import pytest  # noqa: I001
from httpx import AsyncClient, ASGITransport

from app.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the health check endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
