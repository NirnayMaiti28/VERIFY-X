"""
VERIFY-X 2.0 — Query Generation Service

Generates multiple search queries from a normalized claim
for multi-source retrieval.
"""

from __future__ import annotations

import re
from typing import Optional

from app.schemas.verification import ClaimAnalysis, Language


class QueryService:
    """Generates search queries from structured claim analysis."""

    def generate_queries(
        self,
        claim_analysis: ClaimAnalysis,
        max_queries: int = 5,
    ) -> list[str]:
        """Generate multiple search queries from a claim.
        
        Strategy:
        1. Direct claim query (cleaned)
        2. Entity + date query
        3. Entity + event type query
        4. Specific keyword combinations
        5. Fact-check specific query
        
        Uses deterministic templates — no LLM dependency.
        """
        queries: list[str] = []
        claim = claim_analysis.normalized_claim
        entities = claim_analysis.entities
        dates = claim_analysis.dates
        locations = claim_analysis.locations

        # Query 1: Direct claim (shortened if too long)
        direct = self._shorten_query(claim)
        queries.append(direct)

        # Query 2: Entity + date combination
        if entities and dates:
            q = f"{' '.join(entities[:2])} {' '.join(dates[:2])}"
            queries.append(q.strip())

        # Query 3: Entity + location + key verb/noun
        if entities:
            key_terms = self._extract_key_terms(claim)
            if key_terms:
                q = f"{' '.join(entities[:2])} {' '.join(key_terms[:3])}"
                queries.append(q.strip())

        # Query 4: Location + event query
        if locations and dates:
            key_terms = self._extract_key_terms(claim)
            q = f"{' '.join(locations[:2])} {' '.join(key_terms[:2])} {' '.join(dates[:1])}"
            queries.append(q.strip())

        # Query 5: Fact-check specific
        if entities:
            q = f"fact check {' '.join(entities[:2])} {' '.join(dates[:1]) if dates else ''}"
            queries.append(q.strip())

        # Query 6: For non-English, try transliterated/English query
        if claim_analysis.language in (Language.HINDI, Language.BENGALI, Language.CODE_MIXED):
            if entities:
                q = f"{' '.join(entities[:3])} verification"
                queries.append(q.strip())

        # Deduplicate and limit
        seen = set()
        unique_queries = []
        for q in queries:
            q_normalized = q.lower().strip()
            if q_normalized and q_normalized not in seen:
                seen.add(q_normalized)
                unique_queries.append(q)

        return unique_queries[:max_queries]

    def _shorten_query(self, text: str, max_words: int = 12) -> str:
        """Shorten a query to max_words for search API compatibility."""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words])

    def _extract_key_terms(self, text: str) -> list[str]:
        """Extract key terms (nouns, verbs) from claim text.
        
        Simple approach using stopword removal.
        Can be enhanced with POS tagging later.
        """
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "shall", "should", "may", "might", "must", "can",
            "could", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "out", "off", "over", "under",
            "again", "further", "then", "once", "here", "there", "when",
            "where", "why", "how", "all", "both", "each", "few", "more",
            "most", "other", "some", "such", "no", "nor", "not", "only",
            "own", "same", "so", "than", "too", "very", "just", "because",
            "but", "and", "or", "if", "while", "that", "this", "which",
            "what", "who", "whom", "it", "its", "he", "she", "they",
            "them", "their", "we", "our", "you", "your", "my", "his", "her",
        }

        words = re.findall(r'\b\w+\b', text.lower())
        key_terms = [w for w in words if w not in stopwords and len(w) > 2]
        return key_terms
