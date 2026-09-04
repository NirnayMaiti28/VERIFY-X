"""
VERIFY-X 2.0 — Deterministic hashing utilities for cache keys.
"""

from __future__ import annotations

import hashlib


def hash_claim(claim: str) -> str:
    """Generate a deterministic SHA-256 hash for a normalized claim.
    
    Used as cache key for claim lookups. The claim should be normalized
    before hashing (lowercased, whitespace-collapsed, emoji-stripped).
    """
    normalized = claim.strip().lower()
    normalized = " ".join(normalized.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_query(query: str, source: str = "") -> str:
    """Generate a deterministic hash for a search query + source combination.
    
    Used as cache key for search result caching.
    """
    key = f"{source}:{query}".strip().lower()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def hash_content(content: str) -> str:
    """Generate a hash for content deduplication."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
