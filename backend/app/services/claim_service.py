"""
VERIFY-X 2.0 — Claim Normalization Service

Takes raw user input and produces a normalized, structured claim
with extracted entities, dates, locations, numbers, and claim type.
"""

from __future__ import annotations

import re

from app.schemas.verification import ClaimAnalysis, ClaimType, Language
from app.utils.text import clean_text, normalize_whitespace, remove_emojis

# ── Entity Patterns ──

DATE_PATTERNS = [
    r'\b(\d{4})\b',  # Year
    r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',  # DD/MM/YYYY or similar
    r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}\b',
    r'\b\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b',
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s*\d{4}\b',
]

NUMBER_PATTERNS = [
    r'[\$₹€£]\s*[\d,.]+(?:\s*(?:billion|million|trillion|crore|lakh|thousand))?',  # Currency
    r'\b\d+(?:\.\d+)?%\b',  # Percentages
    r'\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b',  # Large numbers with commas
    r'\b\d+(?:\.\d+)?\s*(?:billion|million|trillion|crore|lakh|thousand)\b',  # Number words
]

# Known organizations, countries — extended list for common claims
KNOWN_ENTITIES = {
    # Countries
    "india", "china", "usa", "united states", "pakistan", "bangladesh",
    "russia", "japan", "germany", "france", "uk", "united kingdom",
    "brazil", "australia", "canada", "israel", "iran", "turkey",
    "south korea", "north korea", "sri lanka", "nepal",
    # Organizations
    "who", "un", "united nations", "imf", "world bank", "nasa",
    "isro", "bcci", "icc", "fifa", "olympics",
    "reuters", "bbc", "cnn", "ap", "afp",
    "google", "microsoft", "apple", "meta", "amazon",
    # Indian specific
    "bjp", "congress", "aap", "rbi", "sebi",
}

# Claim type indicators
CLAIM_TYPE_INDICATORS = {
    ClaimType.ECONOMIC: {"gdp", "economy", "inflation", "unemployment", "trade", "deficit", "growth", "recession", "market"},
    ClaimType.POLITICAL: {"election", "vote", "party", "minister", "president", "parliament", "law", "bill", "policy"},
    ClaimType.SCIENTIFIC: {"study", "research", "scientist", "experiment", "discovery", "theory", "vaccine", "climate"},
    ClaimType.STATISTICAL: {"percent", "percentage", "ratio", "average", "median", "survey", "poll", "statistic"},
    ClaimType.HISTORICAL: {"history", "historical", "century", "ancient", "independence", "war", "battle", "revolution"},
    ClaimType.FACTUAL: {"is", "are", "was", "were", "became", "largest", "smallest", "first", "last", "only"},
}


class ClaimService:
    """Normalizes claims and extracts structured metadata."""

    def normalize(self, raw_claim: str, language: Language | None = None) -> ClaimAnalysis:
        """Normalize a raw claim into structured form.
        
        Steps:
        1. Remove emojis (preserving meaningful text)
        2. Clean text (unicode normalization, control chars)
        3. Collapse whitespace
        4. Extract entities, dates, locations, numbers
        5. Classify claim type
        6. Produce normalized claim text
        """
        # Step 1: Remove emojis but preserve text
        de_emojied = remove_emojis(raw_claim)

        # Step 2: Clean text
        cleaned = clean_text(de_emojied)

        # Step 3: Normalize whitespace and excessive punctuation
        normalized = normalize_whitespace(cleaned)
        # Remove excessive punctuation (!!!!, ????) but keep single instances
        normalized = re.sub(r'([!?.])\1+', r'\1', normalized)
        # Remove leading/trailing punctuation clusters
        normalized = normalized.strip('!?.,;: ')

        # Step 4: Extract structured elements
        entities = self._extract_entities(normalized)
        dates = self._extract_dates(normalized)
        locations = self._extract_locations(normalized)
        numbers = self._extract_numbers(normalized)

        # Step 5: Classify claim type
        claim_type = self._classify_claim_type(normalized)

        # Step 6: Detect language if not provided
        if language is None:
            from app.services.language_service import LanguageService
            lang_service = LanguageService()
            language = lang_service.detect(normalized)

        return ClaimAnalysis(
            original_claim=raw_claim,
            normalized_claim=normalized,
            entities=entities,
            dates=dates,
            locations=locations,
            numbers=numbers,
            claim_type=claim_type,
            language=language,
        )

    def _extract_entities(self, text: str) -> list[str]:
        """Extract named entities using pattern matching.
        
        Uses a curated set of known entities plus capitalized word detection.
        This is a deterministic approach — can be enhanced with NER models later.
        """
        found = []
        text_lower = text.lower()

        # Check known entities
        for entity in KNOWN_ENTITIES:
            if entity in text_lower:
                # Find the original-case version
                pattern = re.compile(re.escape(entity), re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    found.append(match.group())

        # Extract capitalized phrases (likely proper nouns)
        # Match 1-3 consecutive capitalized words
        cap_pattern = re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b')
        for match in cap_pattern.finditer(text):
            word = match.group()
            # Skip common sentence starters
            if word.lower() not in {"the", "this", "that", "these", "those", "what", "when", "where", "who", "how"}:  # noqa: SIM102
                if word not in found:
                    found.append(word)

        return list(dict.fromkeys(found))  # Deduplicate preserving order

    def _extract_dates(self, text: str) -> list[str]:
        """Extract date references from text."""
        found = []
        for pattern in DATE_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_str = match.group().strip()
                if date_str not in found:
                    found.append(date_str)
        return found

    def _extract_locations(self, text: str) -> list[str]:
        """Extract location references (countries, cities)."""
        # Simple pattern-based extraction
        # Countries already covered in entities
        locations = []
        text_lower = text.lower()

        location_keywords = {
            "india", "china", "usa", "united states", "pakistan", "bangladesh",
            "russia", "japan", "germany", "france", "uk", "united kingdom",
            "new delhi", "mumbai", "beijing", "washington", "london", "moscow",
            "tokyo", "berlin", "paris", "kolkata", "chennai", "bangalore",
            "hyderabad", "dhaka", "karachi", "lahore", "islamabad",
        }

        for loc in location_keywords:
            if loc in text_lower:
                pattern = re.compile(re.escape(loc), re.IGNORECASE)
                match = pattern.search(text)
                if match:
                    locations.append(match.group())

        return list(dict.fromkeys(locations))

    def _extract_numbers(self, text: str) -> list[str]:
        """Extract numerical values from text."""
        found = []
        for pattern in NUMBER_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                num_str = match.group().strip()
                if num_str not in found:
                    found.append(num_str)
        return found

    def _classify_claim_type(self, text: str) -> ClaimType:
        """Classify the type of claim based on keyword indicators."""
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))

        scores: dict[ClaimType, int] = {}
        for claim_type, indicators in CLAIM_TYPE_INDICATORS.items():
            overlap = words & indicators
            if overlap:
                scores[claim_type] = len(overlap)

        if scores:
            return max(scores, key=scores.get)  # type: ignore
        return ClaimType.FACTUAL  # Default
