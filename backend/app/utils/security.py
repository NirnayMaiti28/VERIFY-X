"""
VERIFY-X 2.0 — Security utilities.
"""

from __future__ import annotations

import re
from ipaddress import ip_address
from urllib.parse import urlparse

# Allowed image MIME types for upload
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
}

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}

# Private/internal IP ranges to block (SSRF protection)
PRIVATE_IP_RANGES = [
    "10.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
    "192.168.",
    "127.",
    "0.",
    "169.254.",
]


def validate_file_type(content_type: str | None, filename: str | None = None) -> bool:
    """Validate that an uploaded file is an allowed image type."""
    if content_type and content_type.lower() in ALLOWED_IMAGE_TYPES:
        return True
    if filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in ALLOWED_IMAGE_EXTENSIONS
    return False


def validate_file_size(size_bytes: int, max_mb: int = 10) -> bool:
    """Validate that file size is within limits."""
    return size_bytes <= max_mb * 1024 * 1024


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch (SSRF protection).
    
    Blocks:
    - Private/internal IP addresses
    - Localhost
    - Non-HTTP(S) schemes
    - URLs without valid hostnames
    """
    try:
        parsed = urlparse(url)

        # Only allow HTTP and HTTPS
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Block localhost
        if hostname in ("localhost", "0.0.0.0", "::1"):
            return False

        # Try to parse as IP address
        try:
            ip = ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
        except ValueError:
            # Not an IP address, check domain-based rules
            for prefix in PRIVATE_IP_RANGES:
                if hostname.startswith(prefix):
                    return False

        return True
    except Exception:  # noqa: BLE001
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal."""
    # Remove directory traversal characters
    filename = filename.replace("..", "").replace("/", "").replace("\\", "")
    # Remove non-ASCII characters
    filename = re.sub(r"[^\w.\-]", "_", filename)
    return filename[:255]  # Limit length
