"""
VERIFY-X 2.0 — Google News RSS Retriever

Primary retrieval provider using Google News RSS feeds.
No API key required.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import feedparser
import httpx

from app.retrieval.base import RetrieverInterface
from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger
from app.utils.text import clean_text, extract_domain

logger = get_logger("retrieval.google_news")

# Language-to-locale mapping for Google News
LANGUAGE_LOCALES = {
    "en": ("en", "US"),
    "hi": ("hi", "IN"),
    "bn": ("bn", "IN"),
    "code-mixed": ("en", "IN"),
}


class GoogleNewsRetriever(RetrieverInterface):
    """Retrieves documents from Google News RSS feeds."""

    @property
    def name(self) -> str:
        return "Google News"

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        max_results: int = 10,
    ) -> list[RetrievedDocument]:
        """Search Google News RSS for the given query."""
        hl, gl = LANGUAGE_LOCALES.get(language, ("en", "US"))
        encoded_query = quote_plus(query)
        rss_url = (
            f"https://news.google.com/rss/search"
            f"?q={encoded_query}"
            f"&hl={hl}&gl={gl}&ceid={gl}:{hl}"
        )

        logger.info("google_news_search", query=query, language=language)

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(rss_url, follow_redirects=True)
                response.raise_for_status()

            feed = feedparser.parse(response.text)
            documents: list[RetrievedDocument] = []

            for entry in feed.entries[:max_results]:
                # Extract publication date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_at = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                # Extract source from title (Google News format: "Title - Source")
                title = entry.get('title', '')
                source = ''
                if ' - ' in title:
                    parts = title.rsplit(' - ', 1)
                    title = parts[0]
                    source = parts[1] if len(parts) > 1 else ''

                # Get the actual link
                link = entry.get('link', '')

                # Extract summary/description
                summary = entry.get('summary', entry.get('description', ''))
                summary = clean_text(summary)

                doc = RetrievedDocument(
                    doc_id=str(uuid.uuid4())[:8],
                    title=clean_text(title),
                    url=link,
                    content=summary,
                    source=source or extract_domain(link) or 'Unknown',
                    published_at=published_at,
                    language=language,
                    retriever=self.name,
                    metadata={
                        "feed_source": "google_news_rss",
                    },
                )
                documents.append(doc)

            logger.info(
                "google_news_results",
                query=query,
                count=len(documents),
            )
            return documents

        except httpx.HTTPError as e:
            logger.error("google_news_http_error", query=query, error=str(e))
            return []
        except Exception as e:
            logger.error("google_news_error", query=query, error=str(e))
            return []
