import sys
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Add the service root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app


@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def mock_ingestion_service():
    """Mock ScrapyIngestionService for testing"""
    with patch('app.api.endpoints.ScrapyIngestionService') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance
