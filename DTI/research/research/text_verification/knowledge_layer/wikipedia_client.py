import time
from urllib.parse import quote

import requests

from text_verification.knowledge_layer.cache import TTLCache


USER_AGENT = "NewsVerifier/1.0 (your@email.com)"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/api/rest_v1"


class WikipediaClient:
    def __init__(self, ttl_seconds=86400, timeout=10):
        self.cache = TTLCache(ttl_seconds=ttl_seconds)
        self.timeout = int(timeout)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _request_with_retries(self, url, max_retries=3):
        for attempt in range(max_retries):
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code == 404:
                return response

            if response.status_code == 429:
                if attempt == max_retries - 1:
                    response.raise_for_status()
                time.sleep(2 ** attempt)
                continue

            response.raise_for_status()
            return response

        raise RuntimeError("Wikipedia request retries exhausted")

    def _fallback_with_package(self, entity):
        try:
            import wikipediaapi

            wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language="en")
            page = wiki.page(entity)
            if not page.exists():
                return {
                    "title": entity,
                    "extract": "",
                    "wikipedia_url": "",
                    "exists": False,
                }

            return {
                "title": page.title,
                "extract": (page.summary or "").strip(),
                "wikipedia_url": page.fullurl,
                "exists": True,
            }
        except Exception:
            return {
                "title": entity,
                "extract": "",
                "wikipedia_url": "",
                "exists": False,
            }

    def fetch_summary(self, entity):
        normalized = (entity or "").strip()
        cache_key = normalized.lower()
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if not normalized:
            result = {
                "title": "",
                "extract": "",
                "wikipedia_url": "",
                "exists": False,
            }
            self.cache.set(cache_key, result)
            return result

        title = quote(normalized.replace(" ", "_"))
        url = f"{WIKIPEDIA_BASE_URL}/page/summary/{title}"

        try:
            response = self._request_with_retries(url)
            if response.status_code == 404:
                result = self._fallback_with_package(normalized)
                self.cache.set(cache_key, result)
                return result

            payload = response.json()
            page_url = (
                payload.get("content_urls", {})
                .get("desktop", {})
                .get("page", "")
            )
            result = {
                "title": payload.get("title") or normalized,
                "extract": (payload.get("extract") or "").strip(),
                "wikipedia_url": page_url,
                "exists": True,
            }
        except Exception:
            result = self._fallback_with_package(normalized)

        self.cache.set(cache_key, result)
        return result


__all__ = ["WikipediaClient"]
