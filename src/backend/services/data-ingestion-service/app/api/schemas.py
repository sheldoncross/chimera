from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class NewsArticle(BaseModel):
    source: str
    title: str
    url: HttpUrl
    content: str
    author: Optional[str] = None
    published_at: Optional[str] = None

class IngestedNewsResponse(BaseModel):
    status: str
    message: str
    article_count: int
