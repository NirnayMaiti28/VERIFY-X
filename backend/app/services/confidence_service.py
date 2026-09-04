"""
VERIFY-X 2.0 — Confidence Calibration Service

Calibrates raw model probabilities to reflect empirical reliability.
Never exposes raw LLM probability as final confidence.
"""

from __future__ import annotations

import math

import numpy as np

from app.utils.logging import get_logger

logger = get_logger("services.confidence")


class ConfidenceService:
    """Calibrates model confidence scores.
    
    Implements temperature scaling for confidence calibration.
    Raw LLM probability is NOT the final confidence.
    """

    def __init__(self, temperature: float = 1.5):
        """Initialize with temperature parameter.
        
        Higher temperature = more conservative (lower) confidence.
        Should be tuned on validation data using ECE/Brier score.
        """
        self.temperature = temperature

    def calibrate(
        self,
        raw_confidence: float,
        evidence_relevance: float = 0.0,
        source_credibility: float = 0.0,
        agreement_score: float = 0.0,
        temporal_consistency: float = 1.0,
        numerical_consistency: float | None = None,
        evidence_count: int = 0,
    ) -> float:
        """Calibrate confidence using temperature scaling + evidence signals.
        
        Final confidence is a weighted combination of:
        1. Temperature-scaled model confidence
        2. Evidence relevance
        3. Source credibility
        4. Cross-source agreement
        5. Temporal consistency
        6. Numerical consistency (if applicable)
        7. Evidence quantity penalty/bonus
        
        Args:
            raw_confidence: Raw model prediction confidence [0, 1]
            evidence_relevance: Average relevance of selected evidence [0, 1]
            source_credibility: Aggregate source credibility [0, 1]
            agreement_score: Cross-source agreement score [0, 1]
            temporal_consistency: Temporal consistency score [0, 1]
            numerical_consistency: Numerical consistency score [0, 1] or None
            evidence_count: Number of evidence items
            
        Returns:
            Calibrated confidence in [0, 1]
        """
        # Step 1: Temperature scaling on raw confidence
        # Transform raw confidence through temperature-scaled softmax-like scaling
        if raw_confidence <= 0:
            scaled = 0.0
        elif raw_confidence >= 1:
            scaled = 1.0
        else:
            # Apply temperature scaling
            logit = math.log(raw_confidence / (1 - raw_confidence + 1e-8))
            scaled_logit = logit / self.temperature
            scaled = 1 / (1 + math.exp(-scaled_logit))

        # Step 2: Evidence quantity adjustment
        if evidence_count == 0:
            evidence_penalty = 0.3  # Heavy penalty for no evidence
        elif evidence_count == 1:
            evidence_penalty = 0.7
        elif evidence_count == 2:
            evidence_penalty = 0.85
        else:
            evidence_penalty = 1.0

        # Step 3: Weighted combination
        weights = {
            "model": 0.35,
            "evidence_relevance": 0.15,
            "source_credibility": 0.10,
            "agreement": 0.20,
            "temporal": 0.10,
            "numerical": 0.10,
        }

        components = {
            "model": scaled,
            "evidence_relevance": evidence_relevance,
            "source_credibility": source_credibility,
            "agreement": agreement_score,
            "temporal": temporal_consistency,
        }

        # Include numerical if available, otherwise redistribute weight
        if numerical_consistency is not None:
            components["numerical"] = numerical_consistency
        else:
            # Redistribute numerical weight to model and agreement
            weights["model"] += 0.05
            weights["agreement"] += 0.05
            del weights["numerical"]

        # Calculate weighted average
        calibrated = sum(
            components[k] * weights[k]
            for k in components
        )

        # Apply evidence penalty
        calibrated *= evidence_penalty

        # Clamp to [0, 1]
        calibrated = max(0.0, min(1.0, calibrated))

        return round(calibrated, 4)

    def compute_ece(
        self,
        predicted_confidences: list[float],
        actual_outcomes: list[bool],
        n_bins: int = 10,
    ) -> float:
        """Compute Expected Calibration Error (ECE).
        
        Used for evaluation — not called during normal inference.
        """
        if not predicted_confidences or not actual_outcomes:
            return 0.0

        confidences = np.array(predicted_confidences)
        outcomes = np.array(actual_outcomes, dtype=float)
        n = len(confidences)

        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0

        for i in range(n_bins):
            mask = (confidences >= bin_boundaries[i]) & (confidences < bin_boundaries[i + 1])
            bin_size = mask.sum()
            if bin_size > 0:
                bin_accuracy = outcomes[mask].mean()
                bin_confidence = confidences[mask].mean()
                ece += (bin_size / n) * abs(bin_accuracy - bin_confidence)

        return round(float(ece), 4)

    def compute_brier_score(
        self,
        predicted_confidences: list[float],
        actual_outcomes: list[bool],
    ) -> float:
        """Compute Brier Score.
        
        Lower is better. Range: [0, 1].
        """
        if not predicted_confidences or not actual_outcomes:
            return 0.0

        confidences = np.array(predicted_confidences)
        outcomes = np.array(actual_outcomes, dtype=float)

        return round(float(np.mean((confidences - outcomes) ** 2)), 4)
