from fastapi import status


def test_health_check(client):
    """Test the root endpoint returns health status"""
    response = client.get("/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Data Ingestion Service is running"}


class TestScrapeNewsEndpoint:
    """Tests for the scrape news endpoint"""

    def test_scrape_news_success(self, client, mock_ingestion_service):
        """Test successful news scraping request"""
        response = client.get("/api/v1/scrape/news")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "success",
            "message": "Scraping job has been scheduled."
        }
        mock_ingestion_service.schedule_scrape.assert_called_once_with(start_urls=None)

    def test_scrape_news_with_start_urls(self, client, mock_ingestion_service):
        """Test news scraping with custom start URLs"""
        start_urls = "https://news.ycombinator.com,https://example.com"
        response = client.get(f"/api/v1/scrape/news?start_urls={start_urls}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "success",
            "message": "Scraping job has been scheduled."
        }
        mock_ingestion_service.schedule_scrape.assert_called_once_with(start_urls=start_urls)

    def test_scrape_news_service_exception(self, client, mock_ingestion_service):
        """Test news scraping when service raises exception"""
        mock_ingestion_service.schedule_scrape.side_effect = Exception("Redis connection failed")

        response = client.get("/api/v1/scrape/news")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestClearScrapeQueueEndpoint:
    """Tests for the clear scrape queue endpoint"""

    def test_clear_scrape_queue_success(self, client, mock_ingestion_service):
        """Test successful queue clearing"""
        response = client.get("/api/v1/clear_scrape_queue")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "status": "success",
            "message": "Scrape queue and duplicate filter cleared."
        }
        mock_ingestion_service.clear_scrape_queue_and_dupefilter.assert_called_once()

    def test_clear_scrape_queue_service_exception(self, client, mock_ingestion_service):
        """Test queue clearing when service raises exception"""
        mock_ingestion_service.clear_scrape_queue_and_dupefilter.side_effect = Exception("Redis connection failed")

        response = client.get("/api/v1/clear_scrape_queue")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
