import time
import re
import requests


class WikidataPropertySearch:

    API = "https://www.wikidata.org/w/api.php"
    HEADERS = {
        "User-Agent": "text-verification-research/1.0 (local development)"
    }

    def __init__(self):
        self._property_cache = {}

    def _normalize_tokens(self, text):
        lowered = (text or "").lower()
        raw_tokens = re.findall(r"\b[a-z0-9]+\b", lowered)
        tokens = []

        for token in raw_tokens:
            if len(token) <= 2:
                continue

            if token.endswith("ing") and len(token) > 5:
                token = token[:-3]
            elif token.endswith("ed") and len(token) > 4:
                token = token[:-2]
            elif token.endswith("es") and len(token) > 4:
                token = token[:-2]
            elif token.endswith("s") and len(token) > 3:
                token = token[:-1]

            if token:
                tokens.append(token)

        return tokens

    def _candidate_score(self, relation, candidate):
        rel_tokens = set(self._normalize_tokens(relation))
        if not rel_tokens:
            return 0.0

        label = candidate.get("label") or ""
        description = candidate.get("description") or ""
        aliases = " ".join(alias.get("value", "") for alias in candidate.get("aliases", []) if isinstance(alias, dict))

        label_tokens = set(self._normalize_tokens(label))
        desc_tokens = set(self._normalize_tokens(description))
        alias_tokens = set(self._normalize_tokens(aliases))

        label_overlap = len(rel_tokens & label_tokens) / max(1, len(rel_tokens))
        alias_overlap = len(rel_tokens & alias_tokens) / max(1, len(rel_tokens))
        desc_overlap = len(rel_tokens & desc_tokens) / max(1, len(rel_tokens))

        return (0.7 * label_overlap) + (0.2 * alias_overlap) + (0.1 * desc_overlap)

    def _get_json(self, params, retries=2):
        for attempt in range(retries + 1):
            try:
                response = requests.get(self.API, params=params, headers=self.HEADERS, timeout=5)
                response.raise_for_status()
                return response.json()
            except Exception:
                if attempt == retries:
                    return None
                time.sleep(0.3 * (attempt + 1))

    def search_property(self, relation):
        relation = (relation or "").strip().lower()

        if not relation:
            return None

        if relation in self._property_cache:
            return self._property_cache[relation]

        params = {
            "action": "wbsearchentities",
            "search": relation,
            "language": "en",
            "type": "property",
            "format": "json",
            "limit": 10,
        }

        data = self._get_json(params)
        property_id = None

        if data and data.get("search"):
            candidates = data.get("search") or []

            best = None
            best_score = 0.0

            for candidate in candidates:
                score = self._candidate_score(relation, candidate)
                if best is None or score > best_score:
                    best = candidate
                    best_score = score

            if best is not None and best_score >= 0.2:
                property_id = best.get("id")
            else:
                property_id = candidates[0].get("id")

        self._property_cache[relation] = property_id
        return property_id
        
__all__ = ["WikidataPropertySearch"]