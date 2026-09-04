"""
VERIFY-X 2.0 — Dense Retrieval

Semantic retrieval using sentence-transformers + FAISS.
"""

from __future__ import annotations

import numpy as np

from app.schemas.evidence import RetrievedDocument
from app.utils.logging import get_logger

logger = get_logger("ranking.dense")


class DenseRetriever:
    """Dense semantic retrieval using embeddings and FAISS."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None

    def _load_model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self._model_name)
                logger.info("dense_model_loaded", model=self._model_name)
            except Exception as e:
                logger.error("dense_model_load_error", error=str(e))
                raise

    def rank(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_k: int = 10,
    ) -> list[tuple[RetrievedDocument, float]]:
        """Rank documents by semantic similarity using dense embeddings.
        
        Args:
            query: The search query
            documents: List of retrieved documents
            top_k: Number of top results to return
            
        Returns:
            List of (document, similarity_score) tuples, sorted by score descending
        """
        if not documents:
            return []

        self._load_model()
        if self._model is None:
            logger.warning("dense_model_not_available")
            return [(doc, 0.0) for doc in documents[:top_k]]

        try:
            # Encode query
            query_embedding = self._model.encode(query, normalize_embeddings=True)

            # Encode all document contents
            doc_texts = [doc.content[:512] for doc in documents]  # Limit length
            doc_embeddings = self._model.encode(doc_texts, normalize_embeddings=True, batch_size=32)

            # Compute cosine similarities (since embeddings are normalized, dot product = cosine)
            similarities = np.dot(doc_embeddings, query_embedding)

            # Pair and sort
            scored_docs = list(zip(documents, similarities.tolist()))
            scored_docs.sort(key=lambda x: x[1], reverse=True)

            return scored_docs[:top_k]

        except Exception as e:  # noqa: BLE001
            logger.error("dense_ranking_error", error=str(e))
            return [(doc, 0.0) for doc in documents[:top_k]]

    def build_faiss_index(self, documents: list[RetrievedDocument]) -> object | None:
        """Build a FAISS index for a set of documents.
        
        Returns the FAISS index. Can be used for larger-scale retrieval.
        This is an abstracted interface — can be swapped to Qdrant later.
        """
        self._load_model()
        if self._model is None:
            return None

        try:
            import faiss

            doc_texts = [doc.content[:512] for doc in documents]
            embeddings = self._model.encode(doc_texts, normalize_embeddings=True, batch_size=32)
            embeddings = np.array(embeddings, dtype=np.float32)

            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)  # Inner product (= cosine for normalized)
            index.add(embeddings)

            logger.info("faiss_index_built", num_docs=len(documents), dimension=dimension)
            return index

        except ImportError:
            logger.warning("faiss_not_installed")
            return None
        except Exception as e:  # noqa: BLE001
            logger.error("faiss_index_error", error=str(e))
            return None
