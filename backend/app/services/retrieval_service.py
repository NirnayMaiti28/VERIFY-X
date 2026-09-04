"""
VERIFY-X 2.0 — Retrieval Orchestration Service

Coordinates multiple retrieval providers, merges results,
deduplicates, and processes documents.
"""

from __future__ import annotations

import asyncio

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.retrieval.base import RetrieverInterface
from app.retrieval.gdelt import GDELTRetriever
from app.retrieval.google_news import GoogleNewsRetriever
from app.retrieval.newsapi import NewsAPIRetriever
from app.retrieval.wikidata import WikidataRetriever
from app.retrieval.wikipedia import WikipediaRetriever
from app.schemas.evidence import RetrievedDocument
from app.utils.hashing import hash_content
from app.utils.logging import get_logger
from app.utils.security import is_safe_url
from app.utils.text import clean_text

logger = get_logger("retrieval.service")


class RetrievalService:
    """Orchestrates multi-source retrieval with document processing."""

    def __init__(self):
        settings = get_settings()
        self._retrievers: list[RetrieverInterface] = [
            GoogleNewsRetriever(),
            WikipediaRetriever(),
            GDELTRetriever(),
            WikidataRetriever(),
            NewsAPIRetriever(api_key=settings.news_api_key),
        ]

    @property
    def available_retrievers(self) -> list[RetrieverInterface]:
        """Return only retrievers that are currently available."""
        return [r for r in self._retrievers if r.is_available]

    async def retrieve_all(
        self,
        queries: list[str],
        language: str = "en",
        max_results_per_source: int = 5,
    ) -> list[RetrievedDocument]:
        """Run all available retrievers in parallel across all queries.
        
        Pipeline:
        1. Run all retrievers concurrently
        2. Merge results
        3. Deduplicate by URL
        4. Process documents (extract content)
        5. Return processed documents
        """
        all_docs: list[RetrievedDocument] = []

        # Create tasks for all retriever × query combinations
        tasks = []
        for retriever in self.available_retrievers:
            for query in queries:
                tasks.append(
                    self._safe_retrieve(retriever, query, language, max_results_per_source)
                )

        # Run all retrievals concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error("retrieval_task_error", error=str(result))
                continue
            if isinstance(result, list):
                all_docs.extend(result)

        # Deduplicate by URL
        deduped = self._deduplicate(all_docs)

        # Process documents (fetch full content where possible)
        processed = await self._process_documents(deduped)

        logger.info(
            "retrieval_complete",
            total_raw=len(all_docs),
            total_deduped=len(deduped),
            total_processed=len(processed),
        )

        return processed

    async def _safe_retrieve(
        self,
        retriever: RetrieverInterface,
        query: str,
        language: str,
        max_results: int,
    ) -> list[RetrievedDocument]:
        """Safely execute a retriever with error handling."""
        try:
            return await retriever.retrieve(query, language, max_results)
        except Exception as e:  # noqa: BLE001
            logger.error(
                "retriever_error",
                retriever=retriever.name,
                query=query,
                error=str(e),
            )
            return []

    def _deduplicate(self, docs: list[RetrievedDocument]) -> list[RetrievedDocument]:
        """Deduplicate documents by URL and content hash."""
        seen_urls: set[str] = set()
        seen_content: set[str] = set()
        unique: list[RetrievedDocument] = []

        for doc in docs:
            # Normalize URL for dedup
            url_key = doc.url.rstrip("/").lower()
            content_key = hash_content(doc.content) if doc.content else ""

            if url_key in seen_urls:
                continue
            if content_key and content_key in seen_content:
                continue

            seen_urls.add(url_key)
            if content_key:
                seen_content.add(content_key)
            unique.append(doc)

        return unique

    async def _process_documents(
        self,
        docs: list[RetrievedDocument],
        fetch_content: bool = True,
    ) -> list[RetrievedDocument]:
        """Process documents: fetch full content for short snippets.
        
        Pipeline per document:
        1. Check if content is too short (needs fetching)
        2. Fetch full page content (with SSRF protection)
        3. Extract text from HTML
        4. Clean and truncate
        """
        if not fetch_content:
            return docs

        tasks = [self._enrich_document(doc) for doc in docs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed = []
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, RetrievedDocument):
                processed.append(result)

        return processed

    async def _enrich_document(self, doc: RetrievedDocument) -> RetrievedDocument:
        """Fetch and extract full content for a document if content is too short."""
        # Only fetch if content is very short and URL is safe
        if len(doc.content) > 200 or not doc.url or not is_safe_url(doc.url):
            return doc

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers={"User-Agent": "VERIFY-X/2.0 (Fact Verification Research)"},
            ) as client:
                response = await client.get(doc.url)
                response.raise_for_status()

            # Extract text from HTML
            soup = BeautifulSoup(response.text, "lxml")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()

            # Extract article text
            article = soup.find("article") or soup.find("main") or soup.find("body")
            if article:
                paragraphs = article.find_all("p")
                text = " ".join(p.get_text(strip=True) for p in paragraphs)
                if text:
                    doc.content = clean_text(text[:3000])

        except Exception:  # noqa: BLE001, S110
            # Keep original content if fetching fails
            pass

        return doc
