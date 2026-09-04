"""
VERIFY-X 2.0 — Numerical Verification Service

Deterministic numerical analysis: detects and verifies numerical claims
using arithmetic rather than LLM guessing.
"""

from __future__ import annotations

import re

from app.utils.logging import get_logger

logger = get_logger("services.numerical")


class NumericalService:
    """Deterministic numerical verification.
    
    Detects: percentages, dates, currency, GDP, population,
    counts, rankings, ratios, statistics.
    
    Uses computation — not LLM arithmetic.
    """

    def analyze(
        self,
        claim: str,
        evidence_texts: list[str],
    ) -> dict:
        """Perform numerical analysis on claim vs evidence.
        
        Returns:
            dict with detected_numbers, calculations, consistency score
        """
        # Extract numbers from claim
        claim_numbers = self._extract_numbers(claim)

        # Extract numbers from evidence
        evidence_numbers: list[dict] = []
        for i, text in enumerate(evidence_texts):
            nums = self._extract_numbers(text)
            for n in nums:
                n["source_index"] = i
            evidence_numbers.extend(nums)

        # Find matching/contradicting numbers
        calculations: list[dict] = []
        consistency_signals: list[float] = []

        for claim_num in claim_numbers:
            for ev_num in evidence_numbers:
                comparison = self._compare_numbers(claim_num, ev_num)
                if comparison:
                    calculations.append(comparison)
                    consistency_signals.append(comparison.get("agreement", 0.5))

        # Calculate overall consistency
        if consistency_signals:
            consistency = sum(consistency_signals) / len(consistency_signals)
        else:
            consistency = None  # No numerical comparison possible

        return {
            "detected_numbers": claim_numbers,
            "evidence_numbers": evidence_numbers[:10],  # Limit for response size
            "calculations": calculations,
            "consistency": round(consistency, 4) if consistency is not None else None,
        }

    def _extract_numbers(self, text: str) -> list[dict]:
        """Extract structured numerical information from text."""
        numbers: list[dict] = []

        # Percentages: "20%", "20 percent"
        for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(%|percent)', text, re.IGNORECASE):
            numbers.append({
                "value": float(match.group(1)),
                "type": "percentage",
                "raw": match.group(),
                "position": match.start(),
            })

        # Currency: "$1.5 billion", "₹500 crore"
        for match in re.finditer(
            r'([\$₹€£])\s*([\d,.]+)\s*(billion|million|trillion|crore|lakh|thousand)?',
            text, re.IGNORECASE
        ):
            value = float(match.group(2).replace(",", ""))
            multiplier_map = {
                "billion": 1e9, "million": 1e6, "trillion": 1e12,
                "crore": 1e7, "lakh": 1e5, "thousand": 1e3,
            }
            multiplier = match.group(3)
            if multiplier:
                value *= multiplier_map.get(multiplier.lower(), 1)
            numbers.append({
                "value": value,
                "type": "currency",
                "currency": match.group(1),
                "raw": match.group(),
                "position": match.start(),
            })

        # Rankings: "1st", "2nd", "3rd", "#1"
        for match in re.finditer(r'(?:#(\d+)|(\d+)(?:st|nd|rd|th)\s+(?:largest|biggest|smallest|fastest|richest))', text, re.IGNORECASE):
            rank = match.group(1) or match.group(2)
            numbers.append({
                "value": int(rank),
                "type": "ranking",
                "raw": match.group(),
                "position": match.start(),
            })

        # Plain large numbers: "1,234,567"
        for match in re.finditer(r'\b(\d{1,3}(?:,\d{3})+)\b', text):
            value = float(match.group(1).replace(",", ""))
            # Skip if already captured
            if not any(n["position"] == match.start() for n in numbers):
                numbers.append({
                    "value": value,
                    "type": "count",
                    "raw": match.group(),
                    "position": match.start(),
                })

        return numbers

    def _compare_numbers(self, claim_num: dict, evidence_num: dict) -> dict | None:
        """Compare a claim number with an evidence number.
        
        Returns comparison result if the numbers are of compatible types.
        """
        # Only compare same type
        if claim_num.get("type") != evidence_num.get("type"):
            return None

        claim_val = claim_num.get("value", 0)
        evidence_val = evidence_num.get("value", 0)

        if claim_val == 0 and evidence_val == 0:
            return None

        # Calculate difference
        if evidence_val != 0:
            relative_diff = abs(claim_val - evidence_val) / abs(evidence_val)
        else:
            relative_diff = abs(claim_val - evidence_val)

        # Determine agreement
        if relative_diff < 0.01:
            agreement = 1.0
            assessment = "exact_match"
        elif relative_diff < 0.05:
            agreement = 0.9
            assessment = "close_match"
        elif relative_diff < 0.15:
            agreement = 0.7
            assessment = "approximate"
        elif relative_diff < 0.5:
            agreement = 0.3
            assessment = "significant_difference"
        else:
            agreement = 0.0
            assessment = "contradiction"

        return {
            "claim_value": claim_val,
            "evidence_value": evidence_val,
            "type": claim_num.get("type"),
            "relative_difference": round(relative_diff, 4),
            "agreement": agreement,
            "assessment": assessment,
            "claim_raw": claim_num.get("raw", ""),
            "evidence_raw": evidence_num.get("raw", ""),
        }

    def verify_percentage_change(
        self,
        from_value: float,
        to_value: float,
        claimed_change: float,
    ) -> dict:
        """Verify a claimed percentage change using deterministic math.
        
        Example:
        Claim: "Inflation decreased by 20%"
        Evidence: "Inflation fell from 6% to 4.8%"
        Calculation: (4.8 - 6) / 6 = -20% ✓
        """
        if from_value == 0:
            return {
                "verified": False,
                "reason": "Cannot compute percentage change from zero",
            }

        actual_change = ((to_value - from_value) / from_value) * 100
        difference = abs(actual_change - claimed_change)

        return {
            "from_value": from_value,
            "to_value": to_value,
            "claimed_change_pct": claimed_change,
            "actual_change_pct": round(actual_change, 2),
            "difference_pct": round(difference, 2),
            "verified": difference < 1.0,  # Within 1 percentage point
            "formula": f"({to_value} - {from_value}) / {from_value} × 100 = {round(actual_change, 2)}%",
        }
