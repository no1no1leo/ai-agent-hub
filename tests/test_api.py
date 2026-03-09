"""
FastAPI integration tests for AI Agent Marketplace API.
Run with: python -m pytest tests/test_api.py -v
"""
import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from marketplace.api import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient for read-only / lightweight tests."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """GET /health"""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_is_healthy(self, client):
        data = response = client.get("/health")
        body = response.json()
        assert body["status"] == "healthy"

    def test_health_contains_version(self, client):
        body = client.get("/health").json()
        assert "version" in body

    def test_health_contains_market_key(self, client):
        body = client.get("/health").json()
        assert "market" in body


# ---------------------------------------------------------------------------
# Market stats
# ---------------------------------------------------------------------------

class TestStatsEndpoint:
    """GET /api/stats"""

    def test_stats_returns_200(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200

    def test_stats_contains_market_key(self, client):
        body = client.get("/api/stats").json()
        assert "market" in body

    def test_stats_market_has_total_tasks(self, client):
        body = client.get("/api/stats").json()
        assert "total_tasks" in body["market"]

    def test_stats_market_has_total_bids(self, client):
        body = client.get("/api/stats").json()
        assert "total_bids" in body["market"]


# ---------------------------------------------------------------------------
# Dashboard data
# ---------------------------------------------------------------------------

class TestDashboardEndpoint:
    """GET /api/dashboard-data"""

    def test_dashboard_returns_200(self, client):
        response = client.get("/api/dashboard-data")
        assert response.status_code == 200

    def test_dashboard_contains_tasks_key(self, client):
        body = client.get("/api/dashboard-data").json()
        assert "tasks" in body

    def test_dashboard_contains_bids_key(self, client):
        body = client.get("/api/dashboard-data").json()
        assert "bids" in body

    def test_dashboard_contains_stats_key(self, client):
        body = client.get("/api/dashboard-data").json()
        assert "stats" in body

    def test_dashboard_tasks_is_list(self, client):
        body = client.get("/api/dashboard-data").json()
        assert isinstance(body["tasks"], list)

    def test_dashboard_bids_is_list(self, client):
        body = client.get("/api/dashboard-data").json()
        assert isinstance(body["bids"], list)


# ---------------------------------------------------------------------------
# Task creation — POST /tasks
# ---------------------------------------------------------------------------

VALID_TASK_PAYLOAD = {
    "description": "Translate a document",
    "input_data": "hello_world.txt",
    "max_budget": 1.5,
    "expected_tokens": 500,
    "requester_id": "test_user",
    "currency": "USDC",
}


class TestCreateTaskEndpoint:
    """POST /tasks"""

    def test_create_task_valid_returns_success_status(self):
        """Valid payload should return 200 or 201 with a task_id."""
        with TestClient(app) as client:
            response = client.post("/tasks", json=VALID_TASK_PAYLOAD)
            assert response.status_code in (200, 201)

    def test_create_task_valid_returns_task_id(self):
        with TestClient(app) as client:
            body = client.post("/tasks", json=VALID_TASK_PAYLOAD).json()
            assert "task_id" in body
            assert body["task_id"]  # non-empty

    def test_create_task_valid_returns_status_created(self):
        with TestClient(app) as client:
            body = client.post("/tasks", json=VALID_TASK_PAYLOAD).json()
            assert body.get("status") == "created"

    def test_create_task_empty_description_returns_422(self):
        """Empty description should fail Pydantic validation with 422."""
        payload = {**VALID_TASK_PAYLOAD, "description": ""}
        with TestClient(app) as client:
            response = client.post("/tasks", json=payload)
            assert response.status_code == 422

    def test_create_task_whitespace_description_returns_422(self):
        """Whitespace-only description should also fail validation."""
        payload = {**VALID_TASK_PAYLOAD, "description": "   "}
        with TestClient(app) as client:
            response = client.post("/tasks", json=payload)
            assert response.status_code == 422

    def test_create_task_negative_budget_returns_422(self):
        """Negative budget violates the gt=0 field constraint."""
        payload = {**VALID_TASK_PAYLOAD, "max_budget": -1.0}
        with TestClient(app) as client:
            response = client.post("/tasks", json=payload)
            assert response.status_code == 422

    def test_create_task_zero_budget_returns_422(self):
        """Zero budget also violates gt=0."""
        payload = {**VALID_TASK_PAYLOAD, "max_budget": 0.0}
        with TestClient(app) as client:
            response = client.post("/tasks", json=payload)
            assert response.status_code == 422

    def test_create_task_zero_tokens_returns_422(self):
        """Zero expected_tokens violates gt=0."""
        payload = {**VALID_TASK_PAYLOAD, "expected_tokens": 0}
        with TestClient(app) as client:
            response = client.post("/tasks", json=payload)
            assert response.status_code == 422

    def test_create_task_missing_description_returns_422(self):
        """Missing required field should return 422."""
        payload = {k: v for k, v in VALID_TASK_PAYLOAD.items() if k != "description"}
        with TestClient(app) as client:
            response = client.post("/tasks", json=payload)
            assert response.status_code == 422


# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

class TestMetricsEndpoint:
    """GET /metrics"""

    def test_metrics_returns_200(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type_is_prometheus(self, client):
        response = client.get("/metrics")
        # Prometheus format uses text/plain with version header
        assert "text/plain" in response.headers.get("content-type", "")

    def test_metrics_body_is_non_empty(self, client):
        response = client.get("/metrics")
        assert len(response.content) > 0

    def test_metrics_contains_known_metric(self, client):
        """The response should contain at least one known custom metric."""
        response = client.get("/metrics")
        text = response.text
        # At least one of the counters defined in metrics.py should appear
        assert "market_tasks_created_total" in text or "market_active_tasks" in text
