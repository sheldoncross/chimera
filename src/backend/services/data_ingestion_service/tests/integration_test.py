import pytest
from unittest.mock import patch, Mock
from app.services.ingestion import ScrapyIngestionService


class TestIntegration:
    """Simple integration tests for the scraping flow"""

    def test_schedule_scrape_calls_scraping(self):
        """Test that scheduling a scrape actually scrapes URLs"""
        with patch('app.services.ingestion.redis.Redis') as mock_redis:
            service = ScrapyIngestionService()
            
            with patch.object(service, '_scrape_url') as mock_scrape:
                mock_scrape.return_value = [{'title': 'Test', 'url': 'http://test.com'}]
                
                service.schedule_scrape("https://example.com")
                
                # Verify URL was scraped
                mock_scrape.assert_called_once_with('https://example.com')
                
                # Verify article was stored
                mock_redis.return_value.lpush.assert_called_once_with('news:items', str({'title': 'Test', 'url': 'http://test.com'}))

    def test_full_scraping_flow(self):
        """Test the complete scraping flow"""
        with patch('app.services.ingestion.redis.Redis') as mock_redis:
            with patch('app.services.ingestion.requests.get') as mock_get:
                # Mock successful HTTP response
                mock_response = Mock()
                mock_response.text = '<tr class="athing"><td class="title"><a href="http://test.com" class="storylink">Test Title</a></td></tr>'
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
                
                service = ScrapyIngestionService()
                service.schedule_scrape("https://news.ycombinator.com")
                
                # Verify HTTP request was made
                mock_get.assert_called_once_with('https://news.ycombinator.com', timeout=10)
                
                # Verify articles were stored (at least one call to lpush)
                assert mock_redis.return_value.lpush.call_count >= 1