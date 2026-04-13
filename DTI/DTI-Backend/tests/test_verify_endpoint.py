import pytest
import time
from httpx import AsyncClient

from app.main import app
from app.dependencies import get_pipeline
from app.config import settings

# --- MOCK PIPELINE CLASSES ---
class MockSuccessPipeline:
    def __init__(self, response):
        self.response = response
    def verify_claim(self, claim: str):
        self.response["claim"] = claim
        return self.response

class MockErrorPipeline:
    def verify_claim(self, claim: str):
        raise Exception("Simulated AI model crash")

class MockTimeoutPipeline:
    def verify_claim(self, claim: str):
        time.sleep(0.5)  # Sleep long enough to trigger our lowered test timeout
        return {}

# Clean up overrides after every test
@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


# --- TESTS ---
@pytest.mark.asyncio
async def test_verify_valid_claim(client: AsyncClient, mock_pipeline_response):
    app.dependency_overrides[get_pipeline] = lambda: MockSuccessPipeline(mock_pipeline_response)
    
    response = await client.post("/api/v1/verify", json={"claim": "This is a valid test claim."})
    
    assert response.status_code == 200
    data = response.json()
    assert data["claim"] == "This is a valid test claim."
    assert data["verdict"] in ["TRUE", "FALSE", "MOSTLY TRUE", "MOSTLY FALSE", "UNCERTAIN", "UNVERIFIED"]
    assert 0.0 <= data["confidence"] <= 1.0

@pytest.mark.asyncio
async def test_verify_empty_claim(client: AsyncClient):
    response = await client.post("/api/v1/verify", json={"claim": ""})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"

@pytest.mark.asyncio
async def test_verify_too_long_claim(client: AsyncClient):
    long_claim = "A" * 501
    response = await client.post("/api/v1/verify", json={"claim": long_claim})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_verify_pipeline_error(client: AsyncClient):
    app.dependency_overrides[get_pipeline] = lambda: MockErrorPipeline()
    
    response = await client.post("/api/v1/verify", json={"claim": "Will crash"})
    assert response.status_code == 500
    assert response.json()["error"] == "pipeline_error"

@pytest.mark.asyncio
async def test_verify_pipeline_timeout(client: AsyncClient, monkeypatch):
    # Temporarily set timeout to 0.1 seconds for this test
    monkeypatch.setattr(settings, "VERIFY_TIMEOUT_SECONDS", 0.1)
    app.dependency_overrides[get_pipeline] = lambda: MockTimeoutPipeline()
    
    response = await client.post("/api/v1/verify", json={"claim": "Will timeout"})
    assert response.status_code == 504
    assert response.json()["error"] == "verification_timeout"

@pytest.mark.asyncio
async def test_evidence_null_fields_handled(client: AsyncClient, mock_pipeline_response):
    # Strip optional fields to ensure Pydantic handles missing data correctly
    mock_pipeline_response["evidence"] = [{
        "source": "Unknown Blog",
        "title": None,
        "url": None
    }]
    app.dependency_overrides[get_pipeline] = lambda: MockSuccessPipeline(mock_pipeline_response)
    
    response = await client.post("/api/v1/verify", json={"claim": "Test nulls"})
    assert response.status_code == 200
    evidence = response.json()["evidence"][0]
    assert evidence["source"] == "Unknown Blog"
    assert evidence["title"] is None