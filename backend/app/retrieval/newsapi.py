"""
VERIFY-X 2.0 — NewsAPI Retriever

Retrieves documents from NewsAPI.org (requires API key).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import httpx

from app.retrieval.base import RetrieverInterface
from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger("retrieval.newsapi")

NEWSAPI_BASE = "https://newsapi.org/v2/everything"


class NewsAPIRetriever(RetrieverInterface):
    """Retrieves documents from NewsAPI.org."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "NewsAPI"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        max_results: int = 10,
    ) -> list[RetrievedDocument]:
        """Search NewsAPI for articles."""
        if not self._api_key:
            logger.warning("newsapi_no_key", message="NewsAPI key not configured, skipping")
            return []

        # NewsAPI only supports a limited set of languages
        newsapi_lang = {"en": "en", "hi": "hi"}.get(language, "en")

        params = {
            "q": query,
            "language": newsapi_lang,
            "pageSize": max_results,
            "sortBy": "relevancy",
        }
        headers = {"X-Api-Key": self._api_key}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(NEWSAPI_BASE, params=params, headers=headers)
                response.raise_for_status()

            data = response.json()

            if data.get("status") != "ok":
                logger.warning("newsapi_status_error", status=data.get("status"))
                return []

            articles = data.get("articles", [])
            documents: list[RetrievedDocument] = []

            for article in articles[:max_results]:
                published_at = None
                pub_str = article.get("publishedAt", "")
                if pub_str:
                    try:
                        published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    except Exception:
                        pass

                content = article.get("content", "") or article.get("description", "") or ""

                doc = RetrievedDocument(
                    doc_id=str(uuid.uuid4())[:8],
                    title=clean_text(article.get("title", "")),
                    url=article.get("url", ""),
                    content=clean_text(content),
                    source=article.get("source", {}).get("name", ""),
                    published_at=published_at,
                    language=language,
                    retriever=self.name,
                    metadata={
                        "author": article.get("author", ""),
                        "source_id": article.get("source", {}).get("id", ""),
                    },
                )
                documents.append(doc)

            logger.info("newsapi_results", query=query, count=len(documents))
            return documents

        except httpx.HTTPError as e:
            logger.error("newsapi_http_error", query=query, error=str(e))
            return []
        except Exception as e:
            logger.error("newsapi_error", query=query, error=str(e))
            return []
