"""
VERIFY-X 2.0 — Ranking Orchestration Service

Coordinates hybrid retrieval: BM25 → Dense → Merge → Deduplicate → Rerank → Select.
"""

from __future__ import annotations

from typing import Optional

from app.ranking.bm25 import BM25Ranker
from app.ranking.dense import DenseRetriever
from app.ranking.reranker import CrossEncoderReranker
from app.schemas.evidence import EvidenceItem, EvidenceStance, RetrievedDocument
from app.utils.logging import get_logger
from app.utils.text import extract_domain

logger = get_logger("ranking.service")


class RankingService:
    """Orchestrates hybrid retrieval and ranking pipeline."""

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        bm25_weight: float = 0.3,
        dense_weight: float = 0.7,
    ):
        self.bm25 = BM25Ranker()
        self.dense = DenseRetriever(model_name=embedding_model)
        self.reranker = CrossEncoderReranker(model_name=reranker_model)
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight

    def rank_and_select(
        self,
        query: str,
        documents: list[RetrievedDocument],
        max_candidates: int = 20,
        top_k_evidence: int = 5,
    ) -> list[EvidenceItem]:
        """Full hybrid ranking pipeline.
        
        Pipeline:
        1. BM25 ranking
        2. Dense embedding ranking
        3. Merge scores with configurable weights
        4. Deduplicate
        5. Cross-encoder reranking on top candidates
        6. Select top-k evidence
        7. Format as EvidenceItems
        """
        if not documents:
            return []

        logger.info(
            "ranking_started",
            total_documents=len(documents),
            max_candidates=max_candidates,
            top_k=top_k_evidence,
        )

        # Step 1: BM25 ranking
        bm25_results = self.bm25.rank(query, documents, top_k=max_candidates)
        bm25_scores = {id(doc): score for doc, score in bm25_results}

        # Step 2: Dense ranking
        dense_results = self.dense.rank(query, documents, top_k=max_candidates)
        dense_scores = {id(doc): score for doc, score in dense_results}

        # Step 3: Merge scores
        merged_scores: dict[int, tuple[RetrievedDocument, float]] = {}
        for doc in documents:
            doc_id = id(doc)
            bm25_score = bm25_scores.get(doc_id, 0.0)
            dense_score = dense_scores.get(doc_id, 0.0)

            # Normalize BM25 scores to [0, 1]
            max_bm25 = max((s for _, s in bm25_results), default=1.0) or 1.0
            bm25_normalized = bm25_score / max_bm25

            combined = (
                self.bm25_weight * bm25_normalized
                + self.dense_weight * dense_score
            )
            merged_scores[doc_id] = (doc, combined)

        # Sort by merged score
        sorted_candidates = sorted(
            merged_scores.values(),
            key=lambda x: x[1],
            reverse=True,
        )[:max_candidates]

        candidate_docs = [doc for doc, _ in sorted_candidates]

        # Step 4: Cross-encoder reranking
        reranked = self.reranker.rerank(query, candidate_docs, top_k=top_k_evidence)

        # Step 5: Format as EvidenceItems
        evidence_items: list[EvidenceItem] = []
        for i, (doc, score) in enumerate(reranked):
            evidence_items.append(
                EvidenceItem(
                    evidence_id=f"E{i + 1}",
                    source=doc.source or extract_domain(doc.url) or "Unknown",
                    title=doc.title,
                    url=doc.url,
                    published_at=doc.published_at,
                    passage=doc.content[:1000],  # Limit passage length
                    relevance_score=round(score, 4),
                    stance=EvidenceStance.NEUTRAL,  # Stance will be determined by verdict engine
                    language=doc.language,
                    retriever=doc.retriever,
                )
            )

        logger.info(
            "ranking_complete",
            candidates=len(candidate_docs),
            selected=len(evidence_items),
        )

        return evidence_items
