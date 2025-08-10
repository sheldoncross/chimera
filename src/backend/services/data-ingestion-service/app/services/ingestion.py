import os
import redis

class ScrapyIngestionService:
    def __init__(self):
        os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'app.services.scraper.settings')
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )

    def schedule_scrape(self, start_urls=None):
        if start_urls:
            urls = start_urls.split(',')
        else:
            urls = ['https://news.ycombinator.com']
        
        for url in urls:
            self.redis_client.lpush('news:start_urls', url)

    def clear_scrape_queue_and_dupefilter(self):
        self.redis_client.delete('news:start_urls')
        self.redis_client.delete('news:dupefilter')
