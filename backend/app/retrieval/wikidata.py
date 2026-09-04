"""
VERIFY-X 2.0 — Wikidata Retriever

Retrieves structured facts from Wikidata for entity verification.
"""

from __future__ import annotations

import uuid

import httpx

from app.retrieval.base import RetrieverInterface
from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger

logger = get_logger("retrieval.wikidata")

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


class WikidataRetriever(RetrieverInterface):
    """Retrieves structured facts from Wikidata."""

    @property
    def name(self) -> str:
        return "Wikidata"

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        max_results: int = 5,
    ) -> list[RetrievedDocument]:
        """Search Wikidata for structured entity information."""
        try:
            # Search for entities
            params = {
                "action": "wbsearchentities",
                "format": "json",
                "language": language if language in ("en", "hi", "bn") else "en",
                "search": query,
                "limit": max_results,
                "type": "item",
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(WIKIDATA_API, params=params)
                response.raise_for_status()

            data = response.json()
            results = data.get("search", [])
            documents: list[RetrievedDocument] = []

            for item in results:
                entity_id = item.get("id", "")
                label = item.get("label", "")
                description = item.get("description", "")
                url = item.get("concepturi", f"https://www.wikidata.org/wiki/{entity_id}")

                content = f"{label}: {description}" if description else label

                doc = RetrievedDocument(
                    doc_id=str(uuid.uuid4())[:8],
                    title=label,
                    url=url,
                    content=content,
                    source="Wikidata",
                    language=language,
                    retriever=self.name,
                    metadata={
                        "entity_id": entity_id,
                        "source_type": "knowledge_base",
                    },
                )
                documents.append(doc)

            logger.info("wikidata_results", query=query, count=len(documents))
            return documents

        except httpx.HTTPError as e:
            logger.error("wikidata_http_error", query=query, error=str(e))
            return []
        except Exception as e:  # noqa: BLE001
            logger.error("wikidata_error", query=query, error=str(e))
            return []
