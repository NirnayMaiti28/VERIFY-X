"""
VERIFY-X 2.0 — Verdict Engine

Combines all verification signals to produce the final verdict.
This is the central orchestration point for the verification pipeline.
"""

from __future__ import annotations

from typing import Optional

from app.schemas.evidence import EvidenceItem, EvidenceStance
from app.schemas.verification import (
    SourceAgreement,
    VerdictEnum,
    VerificationSignals,
)
from app.services.confidence_service import ConfidenceService
from app.services.numerical_service import NumericalService
from app.services.source_credibility_service import SourceCredibilityService
from app.services.temporal_service import TemporalService
from app.utils.logging import get_logger

logger = get_logger("services.verdict")


class VerdictService:
    """Verdict engine: combines all verification signals into a final verdict.
    
    Inputs:
    - Claim text and analysis
    - Evidence items (ranked)
    - Model prediction (if available)
    - Retrieval confidence
    - Source credibility
    - Cross-source agreement
    - Temporal analysis
    - Numerical analysis
    
    Outputs:
    - Final verdict
    - Calibrated confidence
    - Reasoning
    - All individual signals
    """

    def __init__(self):
        self.credibility_service = SourceCredibilityService()
        self.temporal_service = TemporalService()
        self.numerical_service = NumericalService()
        self.confidence_service = ConfidenceService()

    def generate_verdict(
        self,
        claim: str,
        claim_dates: list[str],
        evidence: list[EvidenceItem],
        model_prediction: Optional[dict] = None,
    ) -> dict:
        """Generate a complete verdict with all signals.
        
        MANDATORY RULE: No reliable evidence → NOT_ENOUGH_INFORMATION.
        Never force TRUE/FALSE when evidence is insufficient.
        """
        # ── Step 1: Check evidence sufficiency ──
        if not evidence or len(evidence) == 0:
            return self._insufficient_evidence_verdict(claim)

        # ── Step 2: Source credibility ──
        evidence = self.credibility_service.assess_evidence(evidence)
        source_credibility = self.credibility_service.aggregate_credibility(evidence)

        # ── Step 3: Evidence relevance ──
        evidence_relevance = sum(e.relevance_score for e in evidence) / len(evidence) if evidence else 0

        # Check if evidence is actually relevant
        if evidence_relevance < 0.3:
            return self._insufficient_evidence_verdict(claim, note="Retrieved evidence has low relevance to the claim.")

        # ── Step 4: Cross-source agreement ──
        agreement = self._compute_agreement(evidence)

        # ── Step 5: Temporal analysis ──
        temporal_result = self.temporal_service.analyze(
            claim, claim_dates, evidence
        )
        temporal_consistency = temporal_result["temporal_consistency"]

        # ── Step 6: Numerical analysis ──
        evidence_texts = [e.passage for e in evidence]
        numerical_result = self.numerical_service.analyze(claim, evidence_texts)
        numerical_consistency = numerical_result.get("consistency")

        # ── Step 7: Model prediction ──
        model_verdict = None
        model_confidence = 0.0
        if model_prediction:
            model_verdict = model_prediction.get("verdict")
            model_confidence = model_prediction.get("confidence", 0.0)

        # ── Step 8: Determine verdict ──
        verdict, raw_confidence, reasoning = self._determine_verdict(
            evidence=evidence,
            agreement=agreement,
            model_verdict=model_verdict,
            model_confidence=model_confidence,
            temporal_consistency=temporal_consistency,
            numerical_consistency=numerical_consistency,
        )

        # ── Step 9: Calibrate confidence ──
        calibrated_confidence = self.confidence_service.calibrate(
            raw_confidence=raw_confidence,
            evidence_relevance=evidence_relevance,
            source_credibility=source_credibility,
            agreement_score=agreement.contradiction_strength if agreement.refute_count > agreement.support_count else agreement.source_diversity,
            temporal_consistency=temporal_consistency,
            numerical_consistency=numerical_consistency,
            evidence_count=len(evidence),
        )

        # ── Step 10: Build signals ──
        signals = VerificationSignals(
            model_confidence=model_confidence,
            evidence_relevance=round(evidence_relevance, 4),
            source_credibility=round(source_credibility, 4),
            agreement_score=round(
                agreement.support_count / max(agreement.support_count + agreement.refute_count + agreement.neutral_count, 1),
                4,
            ),
            temporal_consistency=round(temporal_consistency, 4),
            numerical_consistency=round(numerical_consistency, 4) if numerical_consistency is not None else 0.0,
        )

        # ── Step 11: Generate summary ──
        summary = self._generate_summary(
            verdict, evidence, agreement, temporal_result, numerical_result
        )

        return {
            "verdict": verdict,
            "confidence": calibrated_confidence,
            "summary": summary,
            "reasoning": reasoning,
            "signals": signals,
            "agreement": agreement,
            "timeline": temporal_result.get("timeline", []),
            "numerical_analysis": numerical_result,
        }

    def _insufficient_evidence_verdict(self, claim: str, note: str = "") -> dict:
        """Return NOT_ENOUGH_INFORMATION when evidence is insufficient."""
        base_msg = "No reliable evidence was found to verify or refute this claim."
        if note:
            base_msg = f"{base_msg} {note}"

        return {
            "verdict": VerdictEnum.NOT_ENOUGH_INFORMATION,
            "confidence": 0.0,
            "summary": base_msg,
            "reasoning": "The verification system requires reliable evidence to make a determination. Without sufficient evidence, the claim cannot be verified.",
            "signals": VerificationSignals(),
            "agreement": SourceAgreement(),
            "timeline": [],
            "numerical_analysis": {},
        }

    def _compute_agreement(self, evidence: list[EvidenceItem]) -> SourceAgreement:
        """Compute cross-source agreement.
        
        Does NOT use naive majority voting.
        Weights by relevance, source quality, and independence.
        """
        support = 0
        refute = 0
        neutral = 0

        # Track unique sources for diversity
        unique_sources: set[str] = set()

        for ev in evidence:
            unique_sources.add(ev.source)

            if ev.stance == EvidenceStance.SUPPORTS:
                support += 1
            elif ev.stance == EvidenceStance.REFUTES:
                refute += 1
            else:
                neutral += 1

        total = support + refute + neutral
        if total == 0:
            return SourceAgreement()

        # Calculate contradiction strength
        if support > 0 and refute > 0:
            contradiction = min(support, refute) / max(support, refute)
        else:
            contradiction = 0.0

        # Source diversity: unique sources / total evidence
        diversity = len(unique_sources) / total if total > 0 else 0

        return SourceAgreement(
            support_count=support,
            refute_count=refute,
            neutral_count=neutral,
            contradiction_strength=round(contradiction, 4),
            source_diversity=round(diversity, 4),
        )

    def _determine_verdict(
        self,
        evidence: list[EvidenceItem],
        agreement: SourceAgreement,
        model_verdict: Optional[str],
        model_confidence: float,
        temporal_consistency: float,
        numerical_consistency: Optional[float],
    ) -> tuple[VerdictEnum, float, str]:
        """Determine the final verdict based on all signals.
        
        Logic:
        1. If model has high-confidence prediction AND agreement supports it → use model
        2. If sources conflict strongly → MISLEADING or PARTIALLY_TRUE
        3. If all sources agree on refutation → FALSE
        4. If all sources agree on support → TRUE
        5. Otherwise → use weighted signal combination
        """
        reasoning_parts: list[str] = []

        # If we have a model prediction with good confidence
        if model_verdict and model_confidence > 0.7:
            try:
                verdict = VerdictEnum(model_verdict)
                reasoning_parts.append(f"Model predicts {verdict.value} with {model_confidence:.0%} confidence.")
            except ValueError:
                verdict = VerdictEnum.NOT_ENOUGH_INFORMATION
        else:
            # Determine from agreement
            total = agreement.support_count + agreement.refute_count + agreement.neutral_count
            if total == 0:
                return VerdictEnum.NOT_ENOUGH_INFORMATION, 0.0, "No evidence stance determined."

            support_ratio = agreement.support_count / total
            refute_ratio = agreement.refute_count / total

            if agreement.contradiction_strength > 0.5:
                # Strong contradiction between sources
                if support_ratio > refute_ratio:
                    verdict = VerdictEnum.PARTIALLY_TRUE
                    reasoning_parts.append("Sources show significant contradiction.")
                else:
                    verdict = VerdictEnum.MISLEADING
                    reasoning_parts.append("Sources show significant contradiction with more refutations.")
            elif refute_ratio > 0.6:
                verdict = VerdictEnum.FALSE
                reasoning_parts.append(f"{agreement.refute_count} out of {total} sources refute the claim.")
            elif support_ratio > 0.6:
                verdict = VerdictEnum.TRUE
                reasoning_parts.append(f"{agreement.support_count} out of {total} sources support the claim.")
            elif agreement.neutral_count == total:
                verdict = VerdictEnum.NOT_ENOUGH_INFORMATION
                reasoning_parts.append("All evidence is neutral — cannot determine veracity.")
            else:
                verdict = VerdictEnum.PARTIALLY_TRUE
                reasoning_parts.append("Mixed evidence prevents a definitive determination.")

            # Calculate raw confidence from agreement strength
            model_confidence = max(support_ratio, refute_ratio)

        # Adjust for temporal issues
        if temporal_consistency < 0.7:
            reasoning_parts.append(f"Temporal consistency is low ({temporal_consistency:.0%}), which may affect the verdict.")

        # Adjust for numerical contradictions
        if numerical_consistency is not None and numerical_consistency < 0.5:
            reasoning_parts.append(f"Numerical analysis shows inconsistency ({numerical_consistency:.0%}).")

        reasoning = " ".join(reasoning_parts)

        return verdict, model_confidence, reasoning

    def _generate_summary(
        self,
        verdict: VerdictEnum,
        evidence: list[EvidenceItem],
        agreement: SourceAgreement,
        temporal_result: dict,
        numerical_result: dict,
    ) -> str:
        """Generate a human-readable summary of the verification."""
        parts = []

        total = agreement.support_count + agreement.refute_count + agreement.neutral_count

        if verdict == VerdictEnum.TRUE:
            parts.append(f"The claim is supported by the available evidence.")
        elif verdict == VerdictEnum.FALSE:
            parts.append(f"The claim is contradicted by the available evidence.")
        elif verdict == VerdictEnum.MISLEADING:
            parts.append(f"The claim is misleading based on the available evidence.")
        elif verdict == VerdictEnum.PARTIALLY_TRUE:
            parts.append(f"The claim is partially supported by the evidence.")
        else:
            parts.append(f"There is not enough evidence to verify this claim.")

        if total > 0:
            parts.append(f"Based on {total} evidence source(s): {agreement.support_count} support, {agreement.refute_count} refute, {agreement.neutral_count} neutral.")

        # Add top source
        if evidence:
            top = evidence[0]
            parts.append(f"Primary source: {top.source}.")

        return " ".join(parts)
