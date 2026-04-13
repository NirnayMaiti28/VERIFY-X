"""
Headline-to-claim normalization and search query generation.

Converts noisy news headlines into clean declarative claims suitable for
fact verification, and produces compact keyword queries for evidence retrieval.
"""

import re


# ---------------------------------------------------------------------------
# Attribution patterns  –  "X says ...", "Report: ...", etc.
# ---------------------------------------------------------------------------

# Matches patterns like "Turkey says", "Experts say", "Officials said"
# NOTE: "states/stated" deliberately excluded — matches "United States" etc.
_ATTRIBUTION_RE = re.compile(
    r"^(?:.*?\b(?:says?|said|claims?|claimed|argues?|argued|reports?|reported|"
    r"announces?|announced|confirms?|confirmed|warns?|warned|suggests?|suggested|"
    r"believes?|believed|contends?|contended|alleges?|alleged|insists?|insisted|"
    r"according\s+to)\b[:\s,]*)",
    re.IGNORECASE,
)

# Matches prefix labels like "Report:", "Opinion:", "Analysis:", "Breaking:",
# "Exclusive:", "Update:", "WATCH:", "LIVE:" etc.
_PREFIX_LABEL_RE = re.compile(
    r"^(?:report|opinion|analysis|editorial|exclusive|breaking|update|watch|live|"
    r"fact\s*check|developing|alert)\s*:\s*",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Informational / non-claim patterns
# ---------------------------------------------------------------------------

_INFORMATIONAL_PATTERNS = [
    re.compile(r"^what\s+to\s+know\s+about\b", re.IGNORECASE),
    re.compile(r"^this\s+is\s+what\s+happened\b", re.IGNORECASE),
    re.compile(r"^here(?:'s|\s+is)\s+what\b", re.IGNORECASE),
    re.compile(r"^everything\s+(?:you\s+need\s+to\s+)?know\s+about\b", re.IGNORECASE),
    re.compile(r"^how\s+to\b", re.IGNORECASE),
    re.compile(r"^why\s+(?:you|we|it)\b", re.IGNORECASE),
    re.compile(r"^who\s+is\b", re.IGNORECASE),
    re.compile(r"^\d+\s+things\s+(?:to|you)\b", re.IGNORECASE),
    re.compile(r"^what\s+(?:is|are|does|do)\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Stopwords for query generation
# ---------------------------------------------------------------------------

_QUERY_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must",
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
    "she", "her", "it", "its", "they", "them", "their",
    "this", "that", "these", "those",
    "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "up", "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "out", "off", "over", "under",
    "and", "but", "or", "nor", "not", "so", "yet",
    "if", "then", "than", "too", "very", "just", "also",
    "no", "as", "all", "any", "each", "every", "both",
    "says", "said", "say", "according",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize_headline_to_claim(headline: str) -> str:
    """Convert a news headline into a clean declarative claim.

    Returns:
        A cleaned claim string, or ``"NOT_A_CLAIM"`` if the headline is not
        a verifiable factual statement (e.g. informational / how-to / opinion
        without a concrete claim).
    """
    text = (headline or "").strip()

    if not text:
        return "NOT_A_CLAIM"

    # 1. Remove prefix labels  ("Opinion: ...", "Report: ...")
    text = _PREFIX_LABEL_RE.sub("", text).strip()

    # 2. Remove attribution  ("Turkey says ...", "Experts say ...")
    text = _ATTRIBUTION_RE.sub("", text).strip()

    # 3. Remove surrounding quotes that often wrap attributed speech
    if len(text) >= 2 and text[0] in ('"', "'", "\u2018", "\u201c") and text[-1] in ('"', "'", "\u2019", "\u201d"):
        text = text[1:-1].strip()

    # 4. Check for informational patterns (after stripping attribution)
    for pattern in _INFORMATIONAL_PATTERNS:
        if pattern.search(text):
            return "NOT_A_CLAIM"

    # 5. Ensure the remaining text is long enough to be a claim
    if len(text.split()) < 3:
        return "NOT_A_CLAIM"

    # 6. Capitalise first letter, strip trailing punctuation quirks
    text = text[0].upper() + text[1:] if text else text
    text = text.rstrip("?!")  # questions / exclamations are not claims

    return text


def generate_search_query(claim: str) -> str:
    """Produce a compact keyword query from a normalised claim.

    Removes stopwords and very short tokens so retrieval focuses on the
    most informative terms (entities, nouns, verbs).

    Example::

        >>> generate_search_query("Family pulled from rubble after US-Israeli strikes on Tehran")
        'Family pulled rubble US-Israeli strikes Tehran'
    """
    if not claim or claim == "NOT_A_CLAIM":
        return ""

    tokens = claim.split()
    keywords = []

    for token in tokens:
        cleaned = token.strip(".,;:!?\'\"()[]{}<>/\\|")
        normalized = cleaned.lower()

        if not cleaned:
            continue

        if normalized in _QUERY_STOPWORDS:
            continue

        if len(cleaned) <= 1:
            continue

        keywords.append(cleaned)

    return " ".join(keywords)


__all__ = ["normalize_headline_to_claim", "generate_search_query"]
