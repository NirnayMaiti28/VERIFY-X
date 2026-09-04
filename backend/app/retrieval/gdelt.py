"""
VERIFY-X 2.0 — GDELT Retriever

Retrieves documents from the GDELT Project DOC API.
No API key required.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import httpx

from app.retrieval.base import RetrieverInterface
from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger("retrieval.gdelt")

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"


class GDELTRetriever(RetrieverInterface):
    """Retrieves documents from the GDELT DOC API."""

    @property
    def name(self) -> str:
        return "GDELT"

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        max_results: int = 10,
    ) -> list[RetrievedDocument]:
        """Search GDELT for news articles."""
        # Map language codes
        sourcelang = {"en": "english", "hi": "hindi", "bn": "bengali"}.get(language, "english")

        params = {
            "query": query,
            "mode": "ArtList",
            "maxrecords": str(max_results),
            "format": "json",
            "sourcelang": sourcelang,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(GDELT_DOC_API, params=params)
                response.raise_for_status()

            data = response.json()
            articles = data.get("articles", [])
            documents: list[RetrievedDocument] = []

            for article in articles[:max_results]:
                # Parse publication date
                published_at = None
                seendate = article.get("seendate", "")
                if seendate:
                    try:
                        published_at = datetime.strptime(seendate[:14], "%Y%m%dT%H%M%S")
                    except Exception:
                        pass

                doc = RetrievedDocument(
                    doc_id=str(uuid.uuid4())[:8],
                    title=clean_text(article.get("title", "")),
                    url=article.get("url", ""),
                    content=clean_text(article.get("title", "")),  # GDELT often only has titles
                    source=article.get("domain", ""),
                    published_at=published_at,
                    language=article.get("language", language),
                    retriever=self.name,
                    metadata={
                        "domain": article.get("domain", ""),
                        "socialimage": article.get("socialimage", ""),
                    },
                )
                documents.append(doc)

            logger.info("gdelt_results", query=query, count=len(documents))
            return documents

        except httpx.HTTPError as e:
            logger.error("gdelt_http_error", query=query, error=str(e))
            return []
        except Exception as e:
            logger.error("gdelt_error", query=query, error=str(e))
            return []
