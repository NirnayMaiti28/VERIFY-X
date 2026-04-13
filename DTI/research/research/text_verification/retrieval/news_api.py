import requests
import time
from text_verification.config.settings import NEWS_API_KEY, NEWS_API_URL


class NewsRetriever:

    def __init__(self):
        self.api_key = NEWS_API_KEY
        self.base_url = NEWS_API_URL

    def search(self, query, page_size=10):
        """
        Fetch news articles related to the query
        """

        if not self.api_key:
            return []

        params = {
            "q": query,
            "apiKey": self.api_key,
            "pageSize": page_size,
            "language": "en",
            "sortBy": "relevancy"
        }

        data = None

        for attempt in range(3):
            try:
                response = requests.get(self.base_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    break
            except requests.RequestException:
                pass

            if attempt < 2:
                time.sleep(0.35 * (attempt + 1))

        if data is None:
            return []

        articles = []

        for article in data.get("articles", []):
            articles.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "content": article.get("content"),
                "source": (article.get("source") or {}).get("name", "Unknown"),
                "url": article.get("url"),
                "published_at": article.get("publishedAt"),
            })

        return articles