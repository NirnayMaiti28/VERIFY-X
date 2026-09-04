"""
VERIFY-X 2.0 — Cross-Encoder Reranker

Reranks candidate passages using a cross-encoder model
to select the strongest evidence.
"""

from __future__ import annotations

from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger

logger = get_logger("ranking.reranker")


class CrossEncoderReranker:
    """Reranks documents using a cross-encoder model for precise relevance scoring."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy-load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self._model_name, max_length=512)
                logger.info("reranker_loaded", model=self._model_name)
            except Exception as e:
                logger.error("reranker_load_error", error=str(e))
                raise

    def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 5,
    ) -> list[tuple[RetrievedDocument, float]]:
        """Rerank documents using cross-encoder.
        
        Takes ~20 candidates and returns ~3-5 strongest evidence passages.
        
        Args:
            query: The original claim or search query
            documents: Candidate documents to rerank
            top_k: Number of top results to return
            
        Returns:
            List of (document, relevance_score) tuples, sorted by score descending
        """
        if not documents:
            return []

        self._load_model()
        if self._model is None:
            logger.warning("reranker_not_available, using original order")
            return [(doc, 0.5) for doc in documents[:top_k]]

        try:
            # Create query-document pairs for cross-encoder
            pairs = [(query, doc.content[:512]) for doc in documents]

            # Score all pairs
            scores = self._model.predict(pairs, batch_size=16)

            # Normalize scores to [0, 1] using sigmoid
            import numpy as np
            normalized_scores = 1 / (1 + np.exp(-np.array(scores)))

            # Pair and sort
            scored_docs = list(zip(documents, normalized_scores.tolist()))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            selected = scored_docs[:top_k]

            logger.info(
                "reranking_complete",
                candidates=len(documents),
                selected=len(selected),
                top_score=selected[0][1] if selected else 0,
            )

            return selected

        except Exception as e:  # noqa: BLE001
            logger.error("reranking_error", error=str(e))
            return [(doc, 0.5) for doc in documents[:top_k]]
