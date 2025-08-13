import os
import redis
import requests
from bs4 import BeautifulSoup

class ScrapyIngestionService:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True
        )

    def schedule_scrape(self, start_urls=None):
        """Actually scrape the URLs and store results in Redis"""
        if start_urls:
            urls = [url.strip() for url in start_urls.split(',')]
        else:
            urls = ['https://news.ycombinator.com']
        
        for url in urls:
            try:
                articles = self._scrape_url(url)
                for article in articles:
                    # Store each article in Redis
                    self.redis_client.lpush('news:items', str(article))
                    
            except Exception as e:
                print(f"Error scraping {url}: {e}")

    def _scrape_url(self, url):
        """Scrape a single URL and return list of articles"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            if 'news.ycombinator.com' in url:
                return self._parse_hackernews(response.text, url)
            else:
                # Basic scraping for other sites
                return self._parse_generic(response.text, url)
                
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return []

    def _parse_hackernews(self, html, base_url):
        """Parse Hacker News articles"""
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        for story in soup.find_all('tr', class_='athing'):
            try:
                # Find the title cell that contains the actual story link (not the rank)
                title_cells = story.find_all('td', class_='title')
                title_cell = None
                for cell in title_cells:
                    if not cell.get('align'):  # Skip the rank cell which has align="right"
                        title_cell = cell
                        break
                
                if not title_cell:
                    continue
                
                # Look for the link in the titleline span
                titleline = title_cell.find('span', class_='titleline')
                if not titleline:
                    continue
                    
                title_link = titleline.find('a')
                if not title_link:
                    continue
                    
                title = title_link.get_text().strip()
                url = title_link.get('href', '')
                
                # Convert relative URLs to absolute
                if url.startswith('/'):
                    url = 'https://news.ycombinator.com' + url
                elif not url.startswith('http'):
                    url = 'https://news.ycombinator.com/' + url
                
                # Get metadata from next row
                story_id = story.get('id')
                author = None
                score = None
                
                if story_id:
                    # Find the subtext row
                    next_row = story.find_next_sibling('tr')
                    if next_row:
                        author_link = next_row.find('a', class_='hnuser')
                        if author_link:
                            author = author_link.get_text().strip()
                        
                        score_span = next_row.find('span', class_='score')
                        if score_span:
                            score = score_span.get_text().replace(' points', '').strip()
                
                articles.append({
                    'title': title,
                    'url': url,
                    'source': 'Hacker News',
                    'author': author,
                    'score': score
                })
                
            except Exception as e:
                print(f"Error parsing story: {e}")
                continue
                
        return articles

    def _parse_generic(self, html, base_url):
        """Basic parsing for non-HN sites"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Simple heuristic: find links that look like articles
        articles = []
        for link in soup.find_all('a', href=True)[:10]:  # Limit to first 10
            title = link.get_text().strip()
            url = link['href']
            
            if len(title) > 10 and url.startswith('http'):  # Basic filtering
                articles.append({
                    'title': title,
                    'url': url,
                    'source': base_url,
                    'author': None,
                    'score': None
                })
        
        return articles


    def clear_scrape_queue_and_dupefilter(self):
        self.redis_client.delete('news:start_urls')
        self.redis_client.delete('news:items')
