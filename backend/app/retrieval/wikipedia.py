"""
VERIFY-X 2.0 — Wikipedia Retriever

Retrieves information from Wikipedia API for fact verification.
No API key required.
"""

from __future__ import annotations

import uuid

import httpx

from app.retrieval.base import RetrieverInterface
from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger
from app.utils.text import clean_text

logger = get_logger("retrieval.wikipedia")

# Wikipedia API endpoints by language
WIKI_API_URLS = {
    "en": "https://en.wikipedia.org/w/api.php",
    "hi": "https://hi.wikipedia.org/w/api.php",
    "bn": "https://bn.wikipedia.org/w/api.php",
}


class WikipediaRetriever(RetrieverInterface):
    """Retrieves documents from Wikipedia."""

    @property
    def name(self) -> str:
        return "Wikipedia"

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        max_results: int = 5,
    ) -> list[RetrievedDocument]:
        """Search Wikipedia and retrieve article extracts."""
        api_url = WIKI_API_URLS.get(language, WIKI_API_URLS["en"])

        # Step 1: Search for matching articles
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "srprop": "snippet|timestamp",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                search_response = await client.get(api_url, params=search_params)
                search_response.raise_for_status()
                search_data = search_response.json()

            results = search_data.get("query", {}).get("search", [])
            if not results:
                return []

            # Step 2: Get extracts for found articles
            titles = [r["title"] for r in results]
            extract_params = {
                "action": "query",
                "format": "json",
                "titles": "|".join(titles),
                "prop": "extracts|info",
                "exintro": True,
                "explaintext": True,
                "exlimit": max_results,
                "inprop": "url",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                extract_response = await client.get(api_url, params=extract_params)
                extract_response.raise_for_status()
                extract_data = extract_response.json()

            pages = extract_data.get("query", {}).get("pages", {})
            documents: list[RetrievedDocument] = []

            for page_id, page in pages.items():
                if page_id == "-1" or "missing" in page:
                    continue

                title = page.get("title", "")
                extract = page.get("extract", "")
                url = page.get("fullurl", f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}")

                if not extract:
                    continue

                doc = RetrievedDocument(
                    doc_id=str(uuid.uuid4())[:8],
                    title=title,
                    url=url,
                    content=clean_text(extract[:2000]),  # Limit content length
                    source="Wikipedia",
                    language=language,
                    retriever=self.name,
                    metadata={
                        "page_id": page_id,
                        "source_type": "encyclopedia",
                    },
                )
                documents.append(doc)

            logger.info("wikipedia_results", query=query, count=len(documents))
            return documents

        except httpx.HTTPError as e:
            logger.error("wikipedia_http_error", query=query, error=str(e))
            return []
        except Exception as e:  # noqa: BLE001
            logger.error("wikipedia_error", query=query, error=str(e))
            return []
