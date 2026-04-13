import re
import requests
import feedparser
from bs4 import BeautifulSoup


class GoogleNewsRetriever:
    """Fetch near real-time evidence from Google News RSS and article pages."""

    RSS_URL = "https://news.google.com/rss/search"
    HEADERS = {
        "User-Agent": "text-verification-research/1.0 (GoogleNewsRetriever)",
    }

    def __init__(self, timeout=8, max_chars=450):
        self.timeout = timeout
        self.max_chars = max(300, min(max_chars, 500))

    def _clean_text(self, text):
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        if len(cleaned) > self.max_chars:
            return cleaned[: self.max_chars]
        return cleaned

    def _extract_main_text(self, html):
        soup = BeautifulSoup(html or "", "html.parser")

        for node in soup(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
            node.decompose()

        candidates = []
        for p in soup.find_all("p"):
            text = self._clean_text(p.get_text(" ", strip=True))
            if len(text) >= 60:
                candidates.append(text)
            if len(candidates) >= 6:
                break

        if not candidates:
            body_text = self._clean_text(soup.get_text(" ", strip=True))
            return body_text[: self.max_chars]

        merged = " ".join(candidates)
        return merged[: self.max_chars]

    def _fetch_article_text(self, url):
        if not url:
            return ""

        try:
            response = requests.get(url, headers=self.HEADERS, timeout=self.timeout)
            if response.status_code != 200:
                return ""
            return self._extract_main_text(response.text)
        except requests.RequestException:
            return ""

    def search(self, query, max_results=5):
        q = (query or "").strip()
        if not q:
            return []

        limit = max(3, min(int(max_results or 5), 5))

        try:
            response = requests.get(
                self.RSS_URL,
                params={"q": q, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                headers=self.HEADERS,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                return []
        except requests.RequestException:
            return []

        feed = feedparser.parse(response.text)
        entries = getattr(feed, "entries", []) or []

        articles = []
        seen_links = set()

        for entry in entries:
            link = (entry.get("link") or "").strip()
            title = self._clean_text(entry.get("title") or "")

            if not link or link in seen_links:
                continue

            seen_links.add(link)
            content = self._fetch_article_text(link)

            if len(content) < 80:
                summary = self._clean_text(entry.get("summary") or "")
                content = summary[: self.max_chars]

            if len(content) < 40:
                continue

            articles.append(
                {
                    "title": title,
                    "description": "Google News RSS",
                    "content": content,
                    "source": "Google News",
                    "url": link,
                    "published_at": entry.get("published") or entry.get("updated"),
                }
            )

            if len(articles) >= limit:
                break

        return articles


__all__ = ["GoogleNewsRetriever"]
