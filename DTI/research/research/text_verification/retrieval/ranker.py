import numpy as np
from datetime import datetime, timezone
import re
from sklearn.metrics.pairwise import cosine_similarity
from text_verification.utils.source_credibility import SourceCredibility


class EvidenceRanker:

    def __init__(self):
        self.model = None
        self.cross_encoder = None
        try:
            from sentence_transformers import SentenceTransformer, CrossEncoder

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception:
            self.model = None
            self.cross_encoder = None

        self.credibility = SourceCredibility()

    def _evidence_text(self, evidence):
        return (
            (evidence.get("title", "") or "")
            + " "
            + (evidence.get("description", "") or "")
            + " "
            + (evidence.get("content", "") or "")
        ).strip()

    def _lexical_overlap(self, claim, evidence_text):
        claim_tokens = set((claim or "").lower().split())
        evidence_tokens = set((evidence_text or "").lower().split())

        if not claim_tokens:
            return 0.0

        overlap = len(claim_tokens & evidence_tokens)
        return overlap / len(claim_tokens)

    def _token_set(self, text):
        tokens = []
        for token in (text or "").lower().replace("-", " ").split():
            cleaned = "".join(ch for ch in token if ch.isalnum())
            if cleaned and len(cleaned) > 2:
                tokens.append(cleaned)
        return set(tokens)

    def _jaccard(self, a, b):
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return (inter / union) if union else 0.0

    def _entity_coverage(self, evidence_text, entity_terms):
        if not entity_terms:
            return 0.0

        text_lower = (evidence_text or "").lower()
        matched = 0

        for term in entity_terms:
            token = (term or "").strip().lower()
            if token and token in text_lower:
                matched += 1

        return matched / len(entity_terms)

    def _parse_published_at(self, value):
        if not value:
            return None

        text = str(value).strip()

        # GDELT seendate can look like: 20240325T191500Z
        if len(text) == 16 and text.endswith("Z") and "T" in text:
            try:
                return datetime.strptime(text, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except Exception:
                return None

        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    def _claim_years(self, claim):
        return [int(y) for y in re.findall(r"\b(1\d{3}|20\d{2}|2100)\b", claim or "")]

    def _is_historical_claim(self, claim):
        years = self._claim_years(claim)
        if not years:
            return False

        latest = max(years)
        now_year = datetime.now(timezone.utc).year
        return latest <= (now_year - 2)

    def _recency_multiplier(self, evidence, claim):
        dt = self._parse_published_at(evidence.get("published_at"))
        if dt is None:
            return 1.0

        age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)

        # Historical claims should not be strongly biased toward recent publications.
        if self._is_historical_claim(claim):
            if age_days <= 30:
                return 0.96
            if age_days >= 365 * 8:
                return 1.06
            return 1.0

        if age_days <= 7:
            return 1.12
        if age_days <= 30:
            return 1.08
        if age_days <= 180:
            return 1.03
        if age_days >= 365 * 5:
            return 0.9

        return 1.0

    def _apply_corroboration(self, ranked):
        if len(ranked) < 2:
            return ranked

        top_n = min(25, len(ranked))
        token_sets = [self._token_set(self._evidence_text(item)) for item in ranked[:top_n]]

        corroboration_counts = [0] * top_n

        for i in range(top_n):
            source_i = (ranked[i].get("source") or "").strip().lower()
            for j in range(i + 1, top_n):
                source_j = (ranked[j].get("source") or "").strip().lower()
                if not source_i or not source_j or source_i == source_j:
                    continue

                if self._jaccard(token_sets[i], token_sets[j]) >= 0.45:
                    corroboration_counts[i] += 1
                    corroboration_counts[j] += 1

        for idx in range(top_n):
            bonus = min(0.12, 0.04 * corroboration_counts[idx])
            ranked[idx]["corroboration_count"] = corroboration_counts[idx]
            ranked[idx]["final_score"] = float(ranked[idx].get("final_score", 0) or 0) * (1.0 + bonus)

        return sorted(ranked, key=lambda x: x.get("final_score", 0), reverse=True)

    def rank(self, claim, evidences, top_k=10, entity_terms=None):
        """
        Rank evidences based on similarity with claim
        """

        if not evidences:
            return []

        # Evidence texts
        evidence_texts = [self._evidence_text(e) for e in evidences]

        if self.model is not None:
            claim_embedding = self.model.encode([claim])
            evidence_embeddings = self.model.encode(evidence_texts)
            similarities = cosine_similarity(claim_embedding, evidence_embeddings)[0]
        else:
            similarities = np.array([self._lexical_overlap(claim, t) for t in evidence_texts])

        ranked = []

        for i, score in enumerate(similarities):
            evidence = evidences[i]
            sim = float(score)
            evidence_text = evidence_texts[i]

            if evidence.get("source", "") == "Wikipedia":
                sim *= 1.08

            source_score = self.credibility.score(evidence.get("source", ""))
            recency = self._recency_multiplier(evidence, claim)
            entity_coverage = self._entity_coverage(evidence_text, entity_terms or [])
            final_score = sim * source_score * recency * (1.0 + (0.12 * entity_coverage))
            evidence["similarity_score"] = sim
            evidence["recency_multiplier"] = recency
            evidence["entity_coverage"] = entity_coverage
            evidence["final_score"] = final_score
            ranked.append(evidence)

        # Sort by final score
        ranked = sorted(ranked, key=lambda x: x["final_score"], reverse=True)

        # Optional stage-2 reranking on top candidates for better precision on hard cases.
        rerank_k = min(20, len(ranked))
        if self.cross_encoder is not None and rerank_k > 1:
            pairs = []
            for evidence in ranked[:rerank_k]:
                pairs.append([claim, self._evidence_text(evidence)])

            try:
                ce_scores = self.cross_encoder.predict(pairs)
            except Exception:
                ce_scores = None

            if ce_scores is not None:
                ce_scores = np.array(ce_scores, dtype=float)
                ce_probs = 1.0 / (1.0 + np.exp(-ce_scores))

                for i, evidence in enumerate(ranked[:rerank_k]):
                    base_score = float(evidence.get("final_score", 0) or 0)
                    ce_score = float(ce_probs[i])

                    # Blend retrieval score and cross-encoder relevance signal.
                    rerank_score = (0.6 * base_score) + (0.4 * ce_score)

                    evidence["cross_encoder_score"] = ce_score
                    evidence["final_score"] = rerank_score

                ranked[:rerank_k] = sorted(
                    ranked[:rerank_k],
                    key=lambda x: x.get("final_score", 0),
                    reverse=True,
                )

                ranked = sorted(ranked, key=lambda x: x.get("final_score", 0), reverse=True)

            ranked = self._apply_corroboration(ranked)

        return ranked[:top_k]