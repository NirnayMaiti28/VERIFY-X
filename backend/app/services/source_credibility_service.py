"""
VERIFY-X 2.0 — Source Credibility Service

Classifies sources into quality tiers (A/B/C) based on domain reputation.
IMPORTANT: Source credibility is ONE verification signal — it never equals truth.
"""

from __future__ import annotations

from app.schemas.evidence import EvidenceItem, SourceTier
from app.utils.logging import get_logger
from app.utils.text import extract_domain

logger = get_logger("services.credibility")

# ── Tier A: Official/institutional, wire services, major public broadcasters ──
TIER_A_DOMAINS = {
    # Wire services
    "reuters.com", "apnews.com", "afp.com",
    # Public broadcasters
    "bbc.com", "bbc.co.uk", "pbs.org", "npr.org", "dw.com",
    # Government & institutional
    "gov.in", "nic.in", "who.int", "un.org", "worldbank.org", "imf.org",
    "nasa.gov", "cdc.gov", "nih.gov",
    # Academic
    "nature.com", "science.org", "thelancet.com", "bmj.com",
    "arxiv.org", "scholar.google.com",
    # Indian official
    "pib.gov.in", "rbi.org.in", "isro.gov.in",
    # Major factcheckers
    "factcheck.org", "snopes.com", "politifact.com",
    "altnews.in", "boomlive.in", "thequint.com",
}

# ── Tier B: Established media organizations ──
TIER_B_DOMAINS = {
    # International
    "nytimes.com", "washingtonpost.com", "theguardian.com",
    "economist.com", "ft.com", "bloomberg.com",
    "aljazeera.com", "france24.com",
    # Indian media
    "thehindu.com", "indianexpress.com", "ndtv.com",
    "hindustantimes.com", "livemint.com", "scroll.in",
    "thewire.in", "theprint.in", "firstpost.com",
    "timesofindia.indiatimes.com",
    # Tech
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
    # Wikipedia (encyclopedia, not news)
    "wikipedia.org", "en.wikipedia.org", "hi.wikipedia.org", "bn.wikipedia.org",
    # Wikidata
    "wikidata.org",
}


class SourceCredibilityService:
    """Assigns source credibility tiers to evidence items.
    
    Tier A: Official government, institutional, wire services, academic
    Tier B: Established media organizations
    Tier C: Unknown websites, blogs, unverified social media
    
    IMPORTANT: Source credibility NEVER equals truth.
    It is only one verification signal among many.
    """

    def assess_source(self, url: str) -> tuple[SourceTier, float]:
        """Assess the credibility tier and trust score of a source URL.
        
        Returns:
            (SourceTier, trust_score) where trust_score is in [0, 1]
        """
        domain = extract_domain(url)
        if not domain:
            return SourceTier.TIER_C, 0.3

        domain_lower = domain.lower()

        # Check Tier A
        for tier_a in TIER_A_DOMAINS:
            if domain_lower == tier_a or domain_lower.endswith(f".{tier_a}"):
                return SourceTier.TIER_A, 0.9

        # Check Tier B
        for tier_b in TIER_B_DOMAINS:
            if domain_lower == tier_b or domain_lower.endswith(f".{tier_b}"):
                return SourceTier.TIER_B, 0.7

        # Check domain-level heuristics
        if domain_lower.endswith((".gov", ".gov.in")):
            return SourceTier.TIER_A, 0.85
        if domain_lower.endswith((".edu", ".ac.in")):
            return SourceTier.TIER_A, 0.8
        if domain_lower.endswith(".org"):
            return SourceTier.TIER_B, 0.6

        # Default: Tier C
        return SourceTier.TIER_C, 0.4

    def assess_evidence(self, evidence: list[EvidenceItem]) -> list[EvidenceItem]:
        """Assess credibility for all evidence items and update their source_tier."""
        for item in evidence:
            tier, _trust = self.assess_source(item.url)
            item.source_tier = tier
        return evidence

    def aggregate_credibility(self, evidence: list[EvidenceItem]) -> float:
        """Calculate aggregate source credibility score across all evidence.
        
        Weighted by relevance_score × trust_score.
        """
        if not evidence:
            return 0.0

        total_weight = 0.0
        weighted_trust = 0.0

        for item in evidence:
            _, trust = self.assess_source(item.url)
            weight = item.relevance_score
            weighted_trust += trust * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return round(weighted_trust / total_weight, 4)
