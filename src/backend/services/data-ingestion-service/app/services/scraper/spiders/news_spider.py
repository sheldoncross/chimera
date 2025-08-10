from scrapy_redis.spiders import RedisSpider

class NewsSpider(RedisSpider):
    name = "news"
    redis_key = 'news:start_urls'

    def parse(self, response):
        """
        Parses the Hacker News front page to extract article titles and URLs.
        """
        for story in response.css('tr.athing'):
            title_element = story.css('.titleline a')
            title = title_element.css('::text').get()
            url = title_element.css('::attr(href)').get()

            if title and url:
                yield {
                    'title': title,
                    'url': response.urljoin(url),
                    'source': 'Hacker News'
                }
