import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.api.main import app

client = TestClient(app)

class TestAPI:
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
    
    def test_health_endpoint(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] in ["healthy", "degraded"]
    
    def test_prediction_endpoint(self):
        test_data = {
            "sleep_hours": 7.0,
            "workload_hours": 8.0,
            "stress_level": 5,
            "screen_time": 6.0,
            "physical_activity": 30,
            "social_interaction": 2.0,
            "meal_quality": 7,
            "productivity_score": 7
        }
        response = client.post("/api/v1/predict", json=test_data)
        assert response.status_code == 200
        result = response.json()
        assert "risk_level" in result
        assert "risk_score" in result
    
    def test_explain_endpoint(self):
        test_data = {
            "sleep_hours": 7.0,
            "workload_hours": 8.0,
            "stress_level": 5,
            "screen_time": 6.0,
            "physical_activity": 30,
            "social_interaction": 2.0,
            "meal_quality": 7,
            "productivity_score": 7
        }
        response = client.post("/api/v1/explain", json=test_data)
        assert response.status_code == 200
        result = response.json()
        assert "explanation" in result
        assert "recommendations" in result
    
    def test_guidance_endpoint(self):
        test_data = {
            "query": "How to reduce stress?",
            "context": {"risk_level": "Medium"}
        }
        response = client.post("/api/v1/guidance", json=test_data)
        assert response.status_code == 200
        result = response.json()
        assert "response" in result
        assert "query" in result

    def test_invalid_prediction_input(self):
        invalid_data = {
            "sleep_hours": 25,  # Invalid: >24
            "workload_hours": 8.0,
            "stress_level": 5,
            "screen_time": 6.0,
            "physical_activity": 30,
            "social_interaction": 2.0,
            "meal_quality": 7,
            "productivity_score": 7
        }
        response = client.post("/api/v1/predict", json=invalid_data)
        assert response.status_code == 422  # Validation error