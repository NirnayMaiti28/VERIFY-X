"""
Explanation generator with NHTM component breakdown.
"""

import re


class ExplanationGenerator:

    def _claim_tokens(self, claim):
        return {
            token.lower()
            for token in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9\-]{1,}\b", claim or "")
            if len(token) >= 3
        }

    def _claim_years(self, claim):
        return set(re.findall(r"\b(1\d{3}|20\d{2}|2100)\b", claim or ""))

    def _specific_tokens(self, claim):
        return {
            token.lower()
            for token in re.findall(r"\b(?=\w*[A-Za-z])(?=\w*\d)[A-Za-z0-9\-]{3,}\b", claim or "")
        }

    def _evidence_text(self, evidence):
        if evidence.get("top_sentences"):
            top_lines = []
            for item in evidence.get("top_sentences", [])[:3]:
                sentence = (item.get("text") or "").strip()
                if sentence:
                    top_lines.append(sentence)
            if top_lines:
                return " ".join(top_lines)

        return (
            evidence.get("content")
            or evidence.get("description")
            or evidence.get("title")
            or ""
        )

    def _coverage_score(self, claim, evidence_text):
        claim_tokens = self._claim_tokens(claim)
        if not claim_tokens:
            return 0.0

        ev_tokens = {
            token.lower()
            for token in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9\-]{1,}\b", evidence_text or "")
            if len(token) >= 3
        }
        if not ev_tokens:
            return 0.0

        return len(claim_tokens & ev_tokens) / max(1, len(claim_tokens))

    def _aligned_nli_score(self, verdict, verification_result):
        if not verification_result:
            return 0.0

        supports = float(verification_result.get("SUPPORTS", 0) or 0)
        refutes = float(verification_result.get("REFUTES", 0) or 0)

        if verdict in ("TRUE", "MOSTLY TRUE", "True"):
            return supports - (0.35 * refutes)

        if verdict in ("FALSE", "MOSTLY FALSE", "False", "Misleading"):
            return refutes - (0.35 * supports)

        return max(supports, refutes)

    def _pick_explanation_evidence(self, claim, verdict, evidence_list, verification_results=None):
        if not evidence_list:
            return None

        claim_years = self._claim_years(claim)
        specific_tokens = self._specific_tokens(claim)

        candidates = []
        for evidence in evidence_list:
            text = self._evidence_text(evidence)
            coverage = self._coverage_score(claim, text)
            text_lower = (text or "").lower()
            has_specific_hit = any(token in text_lower for token in specific_tokens)
            ev_years = set(re.findall(r"\b(1\d{3}|20\d{2}|2100)\b", text or ""))
            has_year_alignment = bool(claim_years and ev_years and not claim_years.isdisjoint(ev_years))

            if coverage >= 0.2 or has_specific_hit or has_year_alignment:
                candidates.append(evidence)

        if not candidates:
            candidates = evidence_list

        best_item = None
        best_score = -1e9

        for idx, evidence in enumerate(candidates):
            text = self._evidence_text(evidence)
            coverage = self._coverage_score(claim, text)
            final_score = float(evidence.get("final_score", 0) or 0)
            similarity = float(evidence.get("similarity_score", 0) or 0)

            verification_result = None
            if verification_results:
                try:
                    original_idx = evidence_list.index(evidence)
                    if original_idx < len(verification_results):
                        verification_result = verification_results[original_idx]
                except ValueError:
                    verification_result = None

            nli_align = self._aligned_nli_score(verdict, verification_result)

            year_bonus = 0.0
            if claim_years:
                ev_years = set(re.findall(r"\b(1\d{3}|20\d{2}|2100)\b", text or ""))
                if ev_years and not claim_years.isdisjoint(ev_years):
                    year_bonus = 0.12
                elif ev_years:
                    year_bonus = -0.1

            score = (
                (0.45 * nli_align)
                + (0.25 * final_score)
                + (0.20 * coverage)
                + (0.10 * similarity)
                + year_bonus
            )

            if score > best_score:
                best_score = score
                best_item = evidence

        return best_item or max(candidates, key=lambda e: e.get("similarity_score", 0))

    def generate(self, claim, verdict, evidence_list, nhtm_components=None, verification_results=None):

        if not evidence_list:
            return "No reliable evidence was found to verify this claim."

        top_evidence = self._pick_explanation_evidence(
            claim,
            verdict,
            evidence_list,
            verification_results=verification_results,
        )

        source = top_evidence.get("source", "a reliable source")

        text = self._evidence_text(top_evidence)

        text = text[:200]

        if verdict in ("TRUE", "True"):
            explanation = (
                f"The claim appears to be supported by information from {source}. "
                f"Evidence suggests: {text}"
            )
        elif verdict == "MOSTLY TRUE":
            explanation = (
                f"The claim is largely supported by information from {source}, "
                f"though some aspects could not be fully confirmed. "
                f"Evidence suggests: {text}"
            )
        elif verdict in ("FALSE", "False"):
            explanation = (
                f"The claim appears to be incorrect according to {source}. "
                f"Evidence indicates: {text}"
            )
        elif verdict in ("MOSTLY FALSE", "Misleading"):
            explanation = (
                f"The claim is largely contradicted by information from {source}. "
                f"Evidence indicates: {text}"
            )
        else:
            explanation = (
                f"There is not enough reliable evidence to verify this claim. "
                f"Related information from {source}: {text}"
            )

        # Append NHTM component breakdown if available
        if nhtm_components and isinstance(nhtm_components, dict):
            semantic_reasons = []
            k = float(nhtm_components.get("K") or 0.0)
            c = float(nhtm_components.get("C") or 0.0)
            x = float(nhtm_components.get("X") or 0.0)
            e_prime = float(nhtm_components.get("E_prime") or 0.0)
            s = float(nhtm_components.get("S") or 0.0)

            if k >= 0.6:
                semantic_reasons.append("matches trusted encyclopedic knowledge")
            elif k <= -0.6:
                semantic_reasons.append("directly contradicts established facts")

            if c >= 0.7:
                semantic_reasons.append("has strong consensus among retrieved sources")
            elif c <= 0.3:
                semantic_reasons.append("lacks consensus among sources")

            if x >= 0.5:
                semantic_reasons.append("faces significant contradictory evidence")

            if e_prime >= 0.7:
                semantic_reasons.append("is backed by strong direct evidence")
            elif e_prime <= 0.2:
                semantic_reasons.append("lacks strong direct evidence")

            if s >= 0.7:
                semantic_reasons.append("relies on highly credible sources")
            elif s <= 0.3:
                semantic_reasons.append("relies on low-credibility sources")

            if semantic_reasons:
                reasoning = " It " + ", and ".join(semantic_reasons) + "."
                explanation += reasoning

            parts = []
            label_map = {
                "E_prime": "Evidence",
                "S": "Source Trust",
                "C": "Consensus",
                "K": "Knowledge",
                "U": "Uncertainty",
                "X": "Contradiction",
                "P_T_E": "Bayesian P",
            }
            for key, label in label_map.items():
                value = nhtm_components.get(key)
                if value is not None:
                    parts.append(f"{label}: {value}")

            if parts:
                explanation += f" | NHTM Breakdown — {', '.join(parts)}"

        return explanation


__all__ = ["ExplanationGenerator"]