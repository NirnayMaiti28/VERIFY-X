import requests
import re

import numpy as np


class WikipediaRetriever:

    SEARCH_API = "https://en.wikipedia.org/w/api.php"
    HEADERS = {
        "User-Agent": "text-verification-research/1.0 (local development)"
    }

    def __init__(self):
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self.model = None

    def _split_sentences(self, text):
        normalized = re.sub(r"\s+", " ", (text or "")).strip()
        if not normalized:
            return []

        chunks = re.split(r"(?<=[.!?])\s+", normalized)
        return [chunk.strip() for chunk in chunks if len(chunk.strip()) >= 25]

    def _lexical_similarity(self, claim, sentence):
        claim_tokens = {
            token.lower()
            for token in re.findall(r"\b\w+\b", claim or "")
            if len(token) > 2
        }
        sentence_tokens = {
            token.lower()
            for token in re.findall(r"\b\w+\b", sentence or "")
            if len(token) > 2
        }

        if not claim_tokens or not sentence_tokens:
            return 0.0

        overlap = len(claim_tokens & sentence_tokens)
        return overlap / len(claim_tokens)

    def _salient_tokens(self, text):
        tokens = []
        for raw in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,}\b", text or ""):
            token = raw.lower().strip("-.")
            if len(token) < 3:
                continue
            if token.isdigit():
                continue
            tokens.append(token)
        return tokens

    def _keyword_coverage(self, claim, text):
        claim_tokens = set(self._salient_tokens(claim))
        if not claim_tokens:
            return 0.0
        text_tokens = set(self._salient_tokens(text))
        if not text_tokens:
            return 0.0
        return len(claim_tokens & text_tokens) / max(1, len(claim_tokens))

    def _semantic_similarity(self, claim, sentences):
        if not sentences:
            return []

        if self.model is None:
            return [self._lexical_similarity(claim, sentence) for sentence in sentences]

        try:
            claim_vec = self.model.encode([claim], normalize_embeddings=True)
            sentence_vecs = self.model.encode(sentences, normalize_embeddings=True)
            similarities = np.dot(sentence_vecs, claim_vec[0])
            return [float(value) for value in similarities]
        except Exception:
            return [self._lexical_similarity(claim, sentence) for sentence in sentences]

    def _top_relevant_sentences(self, claim, content, top_k=5):
        sentences = self._split_sentences(content)
        if not sentences:
            return []

        similarities = self._semantic_similarity(claim, sentences)
        coverages = [self._keyword_coverage(claim, sentence) for sentence in sentences]
        ranked = sorted(
            zip(sentences, similarities, coverages),
            key=lambda item: (0.75 * item[1]) + (0.25 * item[2]),
            reverse=True,
        )

        selected = []
        for sentence, similarity, coverage in ranked:
            if similarity >= 0.3 or len(selected) < top_k:
                selected.append({
                    "text": sentence,
                    "similarity": float(max(0.0, min(1.0, similarity))),
                    "coverage": float(max(0.0, min(1.0, coverage))),
                })
            if len(selected) >= top_k:
                break

        # Ensure at least one sentence with strong lexical relation overlap.
        best_coverage_idx = int(np.argmax(coverages)) if coverages else -1
        if best_coverage_idx >= 0 and coverages[best_coverage_idx] >= 0.25:
            best_sentence = sentences[best_coverage_idx]
            if not any(item.get("text") == best_sentence for item in selected):
                selected.append({
                    "text": best_sentence,
                    "similarity": float(max(0.0, min(1.0, similarities[best_coverage_idx]))),
                    "coverage": float(max(0.0, min(1.0, coverages[best_coverage_idx]))),
                })
                selected = selected[:top_k]

        return selected

    def _page_relevance(self, claim, page):
        if not claim:
            return 0.0

        title = page.get("title") or ""
        top_sentences = page.get("top_sentences") or []

        title_sim = self._lexical_similarity(claim, title)
        best_sentence_sim = 0.0
        snippet_text = " ".join(item.get("text", "") for item in top_sentences)
        coverage = self._keyword_coverage(claim, f"{title} {snippet_text}")
        if top_sentences:
            best_sentence_sim = float(max(item.get("similarity", 0.0) for item in top_sentences))

        # Prefer pages with semantically matching snippets over title-only matches.
        return (0.15 * title_sim) + (0.65 * best_sentence_sim) + (0.20 * coverage)

    def _search_titles(self, query, limit):
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }

        response = requests.get(
            self.SEARCH_API,
            params=params,
            headers=self.HEADERS,
            timeout=6,
        )
        response.raise_for_status()

        data = response.json()
        return [item.get("title") for item in data.get("query", {}).get("search", []) if item.get("title")]

    def _fetch_summary(self, title):
        params = {
            "action": "query",
            "prop": "extracts|info",
            "explaintext": 1,
            "inprop": "url",
            "titles": title,
            "format": "json",
            "utf8": 1,
        }

        response = requests.get(
            self.SEARCH_API,
            params=params,
            headers=self.HEADERS,
            timeout=6,
        )
        response.raise_for_status()

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():
            if page.get("missing"):
                return None

            page_title = page.get("title") or title
            summary = (page.get("extract") or "").strip()
            url = page.get("fullurl") or f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"

            return {
                "title": page_title,
                "content": summary,
                "url": url,
                "source": "Wikipedia",
            }

        return None

    def search(self, query, max_results=5, claim=None):
        """Search Wikipedia for relevant pages."""

        try:
            search_results = self._search_titles(query, max_results)
        except Exception:
            return []

        pages = []

        for title in search_results:
            try:
                if "disambiguation" in (title or "").lower():
                    continue
                page = self._fetch_summary(title)
                if page:
                    if claim:
                        page["top_sentences"] = self._top_relevant_sentences(
                            claim,
                            page.get("content", ""),
                            top_k=5,
                        )
                        page["relevance_score"] = self._page_relevance(claim, page)
                    pages.append(page)
            except requests.RequestException:
                continue
            except Exception:
                # Network/API failures should not break verification flow.
                continue

        if claim:
            pages.sort(key=lambda item: float(item.get("relevance_score", 0.0) or 0.0), reverse=True)
            # Keep only pages with at least weak semantic grounding.
            filtered = [
                page for page in pages
                if (
                    float(page.get("relevance_score", 0.0) or 0.0) >= 0.18
                    and self._keyword_coverage(
                        claim,
                        f"{page.get('title','')} {' '.join(item.get('text','') for item in page.get('top_sentences', []))}",
                    ) >= 0.10
                )
            ]
            if filtered:
                pages = filtered

        return pages[:max_results]


__all__ = ["WikipediaRetriever"]