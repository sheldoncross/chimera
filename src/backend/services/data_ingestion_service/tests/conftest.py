import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock

from app.main import app
from app.api.endpoints import get_ingestion_service

@pytest.fixture
def mock_ingestion_service():
    """Mock ScrapyIngestionService for testing"""
    return Mock()

@pytest.fixture
def client(mock_ingestion_service):
    """Test client for FastAPI app with mocked ingestion service"""
    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion_service
    yield TestClient(app)
    app.dependency_overrides.clear()
