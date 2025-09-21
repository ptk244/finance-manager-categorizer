"""
Basic tests for the Finance Manager API
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "🤖" in data
    assert "version" in data


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_health_check(client):
    """Test API health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_supported_formats(client):
    """Test supported formats endpoint"""
    response = client.get("/api/v1/supported-formats")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "supported_formats" in data
    assert "csv" in data["supported_formats"]


def test_session_status(client):
    """Test session status endpoint"""
    response = client.get("/api/v1/session-status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "status" in data


def test_reset_session(client):
    """Test session reset endpoint"""
    response = client.post("/api/v1/reset-session")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


def test_upload_no_file(client):
    """Test file upload without file"""
    response = client.post("/api/v1/upload-statement")
    assert response.status_code == 422  # Validation error


def test_upload_invalid_file_type(client):
    """Test upload with invalid file type"""
    response = client.post(
        "/api/v1/upload-statement",
        files={"file": ("test.txt", b"invalid content", "text/plain")}
    )
    assert response.status_code == 422


def test_categorize_without_transactions(client):
    """Test categorization without uploaded transactions"""
    response = client.get("/api/v1/categorize-transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "no transactions" in data["message"].lower()


def test_insights_without_data(client):
    """Test insights without categorized data"""
    response = client.get("/api/v1/generate-insights")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "no categorized transactions" in data["message"].lower()


def test_current_transactions_empty(client):
    """Test getting current transactions when empty"""
    response = client.get("/api/v1/current-transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_count"] == 0


def test_service_stats(client):
    """Test service statistics endpoint"""
    response = client.get("/api/v1/service-stats")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "service_stats" in data
    assert "session_stats" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])