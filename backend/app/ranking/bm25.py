"""
VERIFY-X 2.0 — BM25 Ranking

Lexical retrieval using BM25 over document chunks.
"""

from __future__ import annotations

import re
from typing import Optional

from rank_bm25 import BM25Okapi

from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger

logger = get_logger("ranking.bm25")


class BM25Ranker:
    """BM25 lexical ranking for retrieved documents."""

    def rank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 10,
    ) -> list[tuple[RetrievedDocument, float]]:
        """Rank documents using BM25.
        
        Args:
            query: The search query
            documents: List of retrieved documents
            top_k: Number of top results to return
            
        Returns:
            List of (document, bm25_score) tuples, sorted by score descending
        """
        if not documents:
            return []

        # Tokenize documents
        tokenized_docs = [self._tokenize(doc.content) for doc in documents]

        # Build BM25 index
        bm25 = BM25Okapi(tokenized_docs)

        # Score query against all documents
        query_tokens = self._tokenize(query)
        scores = bm25.get_scores(query_tokens)

        # Pair documents with scores and sort
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        return scored_docs[:top_k]

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace + lowering tokenizer."""
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens
