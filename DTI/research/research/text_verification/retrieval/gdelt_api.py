import requests
import time

from text_verification.config.settings import GDELT_API_URL


class GDELTRetriever:

    def __init__(self):
        self.base_url = GDELT_API_URL

    def _normalize_source_name(self, article):
        source_name = (
            article.get("sourceCommonName")
            or article.get("domain")
            or article.get("sourceCountry")
            or "GDELT"
        )

        return str(source_name).strip() or "GDELT"

    def _best_text(self, article):
        # Prefer semantic text fields and avoid metadata-only fields.
        candidate_keys = [
            "snippet",
            "description",
            "seensource",
            "title",
        ]

        for key in candidate_keys:
            value = article.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned and not cleaned.lower().startswith("http"):
                    return cleaned

        return ""

    def search(self, query, max_records=10):
        """Fetch relevant news metadata from GDELT Doc API."""

        if not query:
            return []

        sort_modes = ["HybridRel", "DateDesc"]
        data = None

        for sort_mode in sort_modes:
            params = {
                "query": query,
                "mode": "ArtList",
                "maxrecords": max_records,
                "sort": sort_mode,
                "format": "json",
            }

            for attempt in range(2):
                try:
                    response = requests.get(self.base_url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    break
                except (requests.RequestException, ValueError):
                    if attempt < 1:
                        time.sleep(0.3 * (attempt + 1))

            if data is not None:
                break

        if data is None:
            return []

        articles = []

        for article in data.get("articles", []):
            source_name = self._normalize_source_name(article)
            title = (article.get("title") or "").strip()
            url = article.get("url")

            # Use textual snippet-like fields only; avoid dates/image URLs/domain strings.
            best_text = self._best_text(article)
            description = best_text if best_text != title else ""
            content = " ".join(part for part in [title, description] if part).strip()

            articles.append(
                {
                    "title": title,
                    "description": description,
                    "content": content,
                    "source": source_name,
                    "url": url,
                    "published_at": article.get("seendate"),
                }
            )

        return articles


__all__ = ["GDELTRetriever"]