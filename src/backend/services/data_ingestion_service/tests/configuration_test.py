import pytest
import os
from unittest.mock import patch
from app.services.ingestion import ScrapyIngestionService


class TestConfiguration:
    """Essential configuration tests"""

    def test_redis_default_configuration(self):
        """Test Redis client creation with default configuration"""
        with patch.dict('os.environ', {}, clear=True):
            with patch('app.services.ingestion.redis.Redis') as mock_redis:
                service = ScrapyIngestionService()
                
                # Verify Redis was called with default values
                mock_redis.assert_called_once_with(
                    host='localhost',
                    port=6379,
                    password=None,
                    decode_responses=True
                )

    def test_redis_environment_configuration(self):
        """Test Redis client creation with environment variables"""
        env_vars = {
            'REDIS_HOST': 'redis-server',
            'REDIS_PORT': '6380',
            'REDIS_PASSWORD': 'secret123'
        }
        
        with patch.dict('os.environ', env_vars):
            with patch('app.services.ingestion.redis.Redis') as mock_redis:
                service = ScrapyIngestionService()
                
                # Verify Redis was called with environment values
                mock_redis.assert_called_once_with(
                    host='redis-server',
                    port=6380,
                    password='secret123',
                    decode_responses=True
                )

    def test_ingestion_service_initialization(self):
        """Test ingestion service initializes correctly"""
        with patch('app.services.ingestion.redis.Redis') as mock_redis:
            service = ScrapyIngestionService()
            assert service.redis_client is not None
            assert hasattr(service, 'schedule_scrape')
            assert hasattr(service, '_scrape_url')