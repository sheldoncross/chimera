import pytest
from unittest.mock import Mock, patch
from app.services.ingestion import ScrapyIngestionService
import redis


class TestScrapyIngestionService:
    """Tests for ScrapyIngestionService"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        with patch('app.services.ingestion.redis.Redis') as mock:
            yield mock.return_value

    @pytest.fixture
    def service(self, mock_redis):
        """Create service instance with mocked Redis"""
        return ScrapyIngestionService()

    def test_init_creates_redis_client(self):
        """Test that __init__ creates Redis client with correct config"""
        with patch.dict('os.environ', {'REDIS_HOST': 'test-host', 'REDIS_PORT': '1234', 'REDIS_PASSWORD': 'secret'}):
            with patch('app.services.ingestion.redis.Redis') as mock_redis:
                service = ScrapyIngestionService()
                
                # Verify Redis client was created with environment variables
                mock_redis.assert_called_once_with(
                    host='test-host',
                    port=1234,
                    password='secret',
                    decode_responses=True
                )

    def test_schedule_scrape_default_urls(self, service, mock_redis):
        """Test scraping with default URLs"""
        with patch.object(service, '_scrape_url') as mock_scrape:
            mock_scrape.return_value = [{'title': 'Test Article', 'url': 'http://test.com'}]
            
            service.schedule_scrape()
            
            # Verify URL was scraped
            mock_scrape.assert_called_once_with('https://news.ycombinator.com')
            
            # Verify articles were stored in Redis
            mock_redis.lpush.assert_called_once_with('news:items', str({'title': 'Test Article', 'url': 'http://test.com'}))

    def test_schedule_scrape_custom_urls(self, service, mock_redis):
        """Test scraping with custom URLs"""
        start_urls = "https://example.com,https://test.com"
        
        with patch.object(service, '_scrape_url') as mock_scrape:
            mock_scrape.return_value = [{'title': 'Test', 'url': 'http://test.com'}]
            
            service.schedule_scrape(start_urls=start_urls)
            
            # Verify both URLs were scraped
            assert mock_scrape.call_count == 2
            mock_scrape.assert_any_call('https://example.com')
            mock_scrape.assert_any_call('https://test.com')

    def test_scrape_url_hackernews(self, service):
        """Test scraping Hacker News specifically"""
        mock_html = '''
        <tr class="athing" id="123">
            <td class="title">
                <a href="https://example.com" class="storylink">Test Article</a>
            </td>
        </tr>
        <tr>
            <td>
                <span class="score">42 points</span>
                by <a href="user?id=testuser" class="hnuser">testuser</a>
            </td>
        </tr>
        '''
        
        with patch('app.services.ingestion.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.text = mock_html
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            articles = service._scrape_url('https://news.ycombinator.com')
            
            assert len(articles) == 1
            assert articles[0]['title'] == 'Test Article'
            assert articles[0]['url'] == 'https://example.com'
            assert articles[0]['author'] == 'testuser'
            assert articles[0]['score'] == '42'

    def test_scrape_url_error_handling(self, service):
        """Test error handling during scraping"""
        with patch('app.services.ingestion.requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")
            
            articles = service._scrape_url('https://example.com')
            
            assert articles == []

    def test_clear_scrape_queue(self, service, mock_redis):
        """Test clearing Redis queues"""
        service.clear_scrape_queue_and_dupefilter()
        
        # Verify both keys were deleted
        assert mock_redis.delete.call_count == 2
        mock_redis.delete.assert_any_call('news:start_urls')
        mock_redis.delete.assert_any_call('news:items')