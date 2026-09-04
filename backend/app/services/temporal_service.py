"""
VERIFY-X 2.0 — Temporal Reasoning Service

Implements explicit temporal analysis for time-sensitive claims.
Claims can change over time — this service detects temporal mismatches.
"""

from __future__ import annotations

import re
from datetime import datetime

from app.schemas.evidence import EvidenceItem
from app.schemas.verification import TimelineEvent
from app.utils.logging import get_logger

logger = get_logger("services.temporal")


class TemporalService:
    """Analyzes temporal aspects of claims and evidence."""

    def analyze(
        self,
        claim: str,
        claim_dates: list[str],
        evidence: list[EvidenceItem],
        current_date: datetime | None = None,
    ) -> dict:
        """Perform temporal analysis.
        
        Analyzes:
        - Claim date vs current date
        - Evidence publication dates
        - Temporal consistency
        - Whether the claim might be outdated
        
        Returns:
            dict with temporal_consistency score, timeline, and notes
        """
        if current_date is None:
            current_date = datetime.utcnow()  # noqa: DTZ003

        # Extract years from claim dates
        claim_years = []
        for d in claim_dates:
            years = re.findall(r'\b(19|20)\d{2}\b', str(d))
            claim_years.extend(int(y) for y in years)

        current_year = current_date.year

        # Build timeline
        timeline: list[TimelineEvent] = []

        # Add claim date events
        for year in sorted(set(claim_years)):
            timeline.append(TimelineEvent(
                date=str(year),
                event=f"Claim references year {year}",
                relevance="claim_date",
            ))

        # Add evidence dates
        evidence_dates: list[datetime] = []
        for ev in evidence:
            if ev.published_at:
                evidence_dates.append(ev.published_at if isinstance(ev.published_at, datetime) else datetime.fromisoformat(str(ev.published_at)))
                timeline.append(TimelineEvent(
                    date=str(ev.published_at)[:10],
                    event=f"Evidence from {ev.source}",
                    source=ev.source,
                    relevance="evidence_date",
                ))

        # Calculate temporal consistency
        temporal_consistency = 1.0
        notes: list[str] = []

        # Check if claim references future dates
        for year in claim_years:
            if year > current_year:
                temporal_consistency -= 0.2
                notes.append(f"Claim references future year {year}")

        # Check if claim references very old dates but evidence is recent
        if claim_years and evidence_dates:
            max_claim_year = max(claim_years)
            min(evidence_dates) if evidence_dates else current_date

            # If claim is about distant past but evidence is recent, might be historical
            if max_claim_year < current_year - 5:
                notes.append(f"Claim references {max_claim_year}, which is historical context")

        # Check evidence recency
        if evidence_dates:
            most_recent = max(evidence_dates)
            days_old = (current_date - most_recent).days
            if days_old > 365:
                temporal_consistency -= 0.1
                notes.append(f"Most recent evidence is {days_old} days old")
            if days_old > 730:
                temporal_consistency -= 0.1
                notes.append("Evidence may be outdated (>2 years old)")

        # Clamp consistency to [0, 1]
        temporal_consistency = max(0.0, min(1.0, temporal_consistency))

        # Sort timeline chronologically
        timeline.sort(key=lambda t: t.date)

        return {
            "temporal_consistency": round(temporal_consistency, 4),
            "timeline": timeline,
            "claim_years": claim_years,
            "evidence_recency_days": min((current_date - d).days for d in evidence_dates) if evidence_dates else None,
            "notes": notes,
        }
