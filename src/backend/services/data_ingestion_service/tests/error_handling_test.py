import pytest
from unittest.mock import Mock, patch
import redis
# Removed unused scrapy imports
from app.services.ingestion import ScrapyIngestionService
# Removed unused spider import


class TestErrorHandling:
    """Essential error handling tests"""

    @pytest.fixture
    def service(self):
        """Create service with mocked Redis"""
        with patch('app.services.ingestion.redis.Redis'):
            return ScrapyIngestionService()

    # Removed unused spider fixture

    def test_redis_connection_error_on_schedule(self, service):
        """Test handling Redis connection error during schedule_scrape"""
        # The simplified implementation catches exceptions, so no error is raised
        service.redis_client.lpush.side_effect = redis.ConnectionError("Connection failed")
        
        # Should handle gracefully without raising exception
        service.schedule_scrape()

    def test_redis_connection_error_on_clear(self, service):
        """Test handling Redis connection error during clear_scrape_queue"""
        service.redis_client.delete.side_effect = redis.ConnectionError("Connection failed")
        
        with pytest.raises(redis.ConnectionError):
            service.clear_scrape_queue_and_dupefilter()

    def test_malformed_html_handling(self, service):
        """Test handling malformed HTML during scraping"""
        malformed_html = '<html><body><tr class="athing">'  # Unclosed tags
        
        with patch('app.services.ingestion.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = malformed_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            # Should handle malformed HTML gracefully
            articles = service._scrape_url('https://news.ycombinator.com')
            assert articles == []

    def test_spider_http_error_handling(self, service):
        """Test handling HTTP errors during scraping"""
        with patch('app.services.ingestion.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            # Should handle the exception gracefully
            articles = service._scrape_url('https://example.com')
            assert articles == []

    def test_invalid_redis_port_environment_variable(self):
        """Test behavior with invalid Redis port"""
        with patch.dict('os.environ', {'REDIS_PORT': 'invalid_port'}):
            with pytest.raises(ValueError):
                ScrapyIngestionService()


# Import os for the environment test
import os