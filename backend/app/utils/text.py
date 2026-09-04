"""
VERIFY-X 2.0 — Text utility functions.
"""

from __future__ import annotations

import re
import unicodedata


def clean_text(text: str) -> str:
    """Remove excessive whitespace, normalize unicode, strip control characters."""
    if not text:
        return ""
    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)
    # Remove control characters (keep newlines and tabs)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Collapse multiple spaces
    text = re.sub(r" +", " ", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to max_length, breaking at word boundaries."""
    if len(text) <= max_length:
        return text
    truncated = text[: max_length - len(suffix)]
    # Try to break at last space
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]
    return truncated + suffix


def remove_emojis(text: str) -> str:
    """Remove emoji characters while preserving meaningful text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u200d"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"
        "\u3030"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text)


def normalize_whitespace(text: str) -> str:
    """Normalize all whitespace to single spaces."""
    return " ".join(text.split())


def extract_urls(text: str) -> list[str]:
    """Extract URLs from text."""
    url_pattern = re.compile(
        r"https?://[^\s<>\"')\]]+",
        re.IGNORECASE,
    )
    return url_pattern.findall(text)


def is_devanagari(text: str) -> bool:
    """Check if text contains Devanagari characters (Hindi)."""
    return bool(re.search(r"[\u0900-\u097F]", text))


def is_bengali_script(text: str) -> bool:
    """Check if text contains Bengali characters."""
    return bool(re.search(r"[\u0980-\u09FF]", text))


def extract_domain(url: str) -> str | None:
    """Extract domain from a URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]
        # Remove www prefix
        domain = domain.removeprefix("www.")
        return domain
    except Exception:  # noqa: BLE001
        return None
