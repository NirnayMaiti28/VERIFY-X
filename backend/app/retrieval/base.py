"""
VERIFY-X 2.0 — Retriever Interface

Abstract base class for all retrieval providers.
Every retriever must implement this interface, making providers independently replaceable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.schemas.evidence import RetrievedDocument


class RetrieverInterface(ABC):
    """Abstract base class for document retrieval providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this retriever."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether this retriever is currently available (has API keys, etc.)."""
        return True

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        language: str = "en",
        max_results: int = 10,
    ) -> list[RetrievedDocument]:
        """Retrieve documents matching the query.
        
        Args:
            query: Search query string
            language: ISO 639-1 language code
            max_results: Maximum number of results to return
            
        Returns:
            List of RetrievedDocument objects
        """
        ...

    async def retrieve_multiple(
        self,
        queries: list[str],
        language: str = "en",
        max_results_per_query: int = 5,
    ) -> list[RetrievedDocument]:
        """Retrieve documents for multiple queries and deduplicate.
        
        Default implementation runs queries sequentially.
        Override for parallel execution.
        """
        all_docs: list[RetrievedDocument] = []
        seen_urls: set[str] = set()

        for query in queries:
            docs = await self.retrieve(query, language, max_results_per_query)
            for doc in docs:
                if doc.url not in seen_urls:
                    seen_urls.add(doc.url)
                    all_docs.append(doc)

        return all_docs
