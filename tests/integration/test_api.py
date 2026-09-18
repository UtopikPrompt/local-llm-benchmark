"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from fastapi import FastAPI
from local_llm_benchmark.api.controller import app


class TestAPIClient:
    """Test client fixture."""
    
    def __init__(self, client: TestClient) -> None:
        self.client = client


@pytest.fixture
def api_client() -> AsyncClient:
    """Create async client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client() -> TestClient:
    """Create sync client for API testing."""
    return TestClient(app)


class TestGetDefaults:
    """Tests for GET /api/v1/config/defaults."""
    
    def test_get_defaults_returns_config(self, sync_client: TestClient):
        """Test that GET /api/v1/config/defaults returns benchmark configuration."""
        response = sync_client.get("/api/v1/config/defaults")
        assert response.status_code == 200
        data = response.json()
        assert "engines" in data
        assert "judges" in data
        assert "tasks" in data
        assert "timeout" in data
        assert "max_concurrent" in data
    
    def test_get_defaults_empty_values(self, sync_client: TestClient):
        """Test that defaults return empty arrays for optional fields."""
        response = sync_client.get("/api/v1/config/defaults")
        data = response.json()
        assert data["engines"] == []
        assert data["judges"] == []
        assert data["tasks"] == []


class TestGetEngines:
    """Tests for GET /api/v1/config/engines."""
    
    def test_get_engines_returns_list(self, sync_client: TestClient):
        """Test that GET /api/v1/config/engines returns list of engines."""
        response = sync_client.get("/api/v1/config/engines")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_engines_has_required_fields(self, sync_client: TestClient):
        """Test that engine objects have required fields."""
        response = sync_client.get("/api/v1/config/engines")
        data = response.json()[0]
        assert "id" in data
        assert "name" in data
        assert "type" in data
        assert "model" in data
        assert "config" in data
        assert "status" in data


class TestPostRun:
    """Tests for POST /api/v1/run."""
    
    def test_post_run_success(self, monkeypatch, sync_client: TestClient):
        """Test that POST /api/v1/run returns benchmark results."""
        def mock_post_run(*args, **kwargs):
            return {
                "results": [
                    {
                        "id": "result-1",
                        "challenge_id": "challenge-1",
                        "engine_id": "engine-1",
                        "task_id": "task-1",
                        "quality_score": 0.92,
                        "metrics": {
                            "duration_ms": 100000.0,
                            "engine_tokens_generated": 12000,
                            "engine_cost_usd": 0.36
                        }
                    }
                ],
                "summary": {
                    "total_results": 1,
                    "avg_quality_score": 0.92
                }
            }
        
        monkeypatch.setattr("local_llm_benchmark.api.services.run_benchmark", mock_post_run)
        
        response = sync_client.post("/api/v1/run")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) > 0
    
    def test_post_run_invalid_config(self, sync_client: TestClient):
        """Test that POST /api/v1/run validates configuration."""
        response = sync_client.post("/api/v1/run", json={})
        assert response.status_code == 422  # Validation error
        
        response = sync_client.post("/api/v1/run", json={"invalid_field": "value"})
        assert response.status_code == 422
    
    def test_post_run_missing_required_fields(self, sync_client: TestClient):
        """Test that POST /api/v1/run requires required fields."""
        response = sync_client.post("/api/v1/run", json={"tasks": ".", "engines": []})
        assert response.status_code == 422
        
        response = sync_client.post("/api/v1/run", json={"tasks": ".", "judges": []})
        assert response.status_code == 422


class TestAPIServices:
    """Tests for API services layer."""
    
    def test_new_engine_from_request(self):
        """Test creating engine from API request."""
        from local_llm_benchmark.api.services import create_engine
        
        request = {
            "id": "test-engine",
            "name": "Test Engine",
            "type": "local",
            "model": "llama3:8b",
            "config": {
                "temperature": 0.7,
                "max_tokens": 4096
            }
        }
        
        engine = create_engine(request)
        assert engine is not None
        assert engine.id == "test-engine"
        assert engine.name == "Test Engine"
        assert engine.model == "llama3:8b"
    
    def test_new_judge_from_request_none(self):
        """Test creating judge from None request."""
        from local_llm_benchmark.api.services import create_judge
        
        judge = create_judge(None)
        assert judge is not None
        assert judge.name == "default-judge"
    
    def test_new_judge_from_request(self):
        """Test creating judge from request."""
        from local_llm_benchmark.api.services import create_judge
        
        request = {
            "id": "test-judge",
            "name": "Quality Judge",
            "threshold": 0.85
        }
        
        judge = create_judge(request)
        assert judge.id == "test-judge"
        assert judge.name == "Quality Judge"
        assert judge.threshold == 0.85


class TestAPITypes:
    """Tests for API type definitions."""
    
    def test_engine_schema(self):
        """Test engine schema validation."""
        from local_llm_benchmark.api.schemas.engine import EngineCreate
        
        engine = EngineCreate(
            name="Test Engine",
            model="llama3:8b",
            config={
                "temperature": 0.7,
                "max_tokens": 4096
            }
        )
        assert engine.name == "Test Engine"
        assert engine.model == "llama3:8b"
    
    def test_judge_schema(self):
        """Test judge schema validation."""
        from local_llm_benchmark.api.schemas.engine import JudgeCreate
        
        judge = JudgeCreate(
            name="Quality Judge",
            threshold=0.85
        )
        assert judge.name == "Quality Judge"
        assert judge.threshold == 0.85
    
    def test_result_schema(self):
        """Test result schema validation."""
        from local_llm_benchmark.api.schemas.response import ResultCreate
        
        result = ResultCreate(
            challenge_id="challenge-1",
            engine_id="engine-1",
            task_id="task-1",
            quality_score=0.92,
            safety_score=0.98,
            accuracy_score=0.89
        )
        assert result.challenge_id == "challenge-1"
        assert result.quality_score == 0.92
