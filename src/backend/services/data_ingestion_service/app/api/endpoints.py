from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.services.ingestion import ScrapyIngestionService

router = APIRouter()

def get_ingestion_service():
    return ScrapyIngestionService()

@router.get("/scrape/news")
async def scrape_news(start_urls: Optional[str] = None, service: ScrapyIngestionService = Depends(get_ingestion_service)):
    """
    Schedule a scrape for news articles.
    Optionally provide a comma-separated list of start_urls.
    """
    try:
        service.schedule_scrape(start_urls=start_urls)
        return {"status": "success", "message": "Scraping job has been scheduled."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clear_scrape_queue")
async def clear_scrape_queue(service: ScrapyIngestionService = Depends(get_ingestion_service)):
    """
    Clears the Redis queue for news scraping and the duplicate filter.
    This allows re-scraping of previously scraped URLs.
    """
    try:
        service.clear_scrape_queue_and_dupefilter()
        return {"status": "success", "message": "Scrape queue and duplicate filter cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))