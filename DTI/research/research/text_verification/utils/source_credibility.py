from urllib.parse import urlparse


HIGH_TOKENS = {
    "bbc",
    "reuters",
    "apnews",
    "associated press",
    "nature",
    ".gov",
    ".gouv",
}

MEDIUM_TOKENS = {
    "wikipedia",
    "techcrunch",
    "theverge",
    "wired",
    "arstechnica",
    "engadget",
    "google news",
}

LOW_TOKENS = {
    "blogspot",
    "medium.com",
    "substack",
    "clickbait",
    "rumor",
}


def get_source_credibility(source_url_or_name):
    raw = (source_url_or_name or "").strip().lower()
    if not raw:
        return "Low"

    host = ""
    if "://" in raw:
        try:
            host = (urlparse(raw).netloc or "").lower()
        except Exception:
            host = ""

    combined = " ".join([raw, host]).strip()

    if any(token in combined for token in HIGH_TOKENS):
        return "High"

    if any(token in combined for token in MEDIUM_TOKENS):
        return "Medium"

    if any(token in combined for token in LOW_TOKENS):
        return "Low"

    # Domain heuristics for official sources.
    if host.endswith(".gov") or host.endswith(".mil"):
        return "High"

    if host:
        # Known domain, but uncategorized.
        return "Medium"

    return "Low"


__all__ = ["get_source_credibility"]
