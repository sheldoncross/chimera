from fastapi import APIRouter
from typing import Optional
from app.services.ingestion import ScrapyIngestionService

router = APIRouter()

@router.get("/scrape/news")
async def scrape_news(start_urls: Optional[str] = None):
    """
    Schedule a scrape for news articles.
    Optionally provide a comma-separated list of start_urls.
    """
    service = ScrapyIngestionService()
    service.schedule_scrape(start_urls=start_urls)
    return {"status": "success", "message": "Scraping job has been scheduled."}

@router.get("/clear_scrape_queue")
async def clear_scrape_queue():
    """
    Clears the Redis queue for news scraping and the duplicate filter.
    This allows re-scraping of previously scraped URLs.
    """
    service = ScrapyIngestionService()
    service.clear_scrape_queue_and_dupefilter()
    return {"status": "success", "message": "Scrape queue and duplicate filter cleared."}
