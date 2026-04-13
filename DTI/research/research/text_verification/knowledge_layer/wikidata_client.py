import time

import requests

from text_verification.knowledge_layer.cache import TTLCache


USER_AGENT = "NewsVerifier/1.0 (your@email.com)"
WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
WIKIDATA_SPARQL_URL = "https://query.wikidata.org/sparql"

PREDICATE_TO_PROPERTY = {
    "population": "P1082",
    "date of birth": "P569",
    "country": "P17",
    "head of state": "P35",
    "employer": "P108",
    "member of": "P463",
    "position held": "P39",
    "located in": "P131",
    "location": "P131",
    "located at": "P276",
    "located on": "P706",
    "inception": "P571",
    "instance of": "P31",
    "subclass of": "P279",
    "part of": "P361",
    "made of": "P186",
    "made up of": "P186",
    "composed of": "P186",
    "has part": "P527",
}


class WikidataClient:
    def __init__(self, ttl_seconds=86400, timeout=12):
        self.cache = TTLCache(ttl_seconds=ttl_seconds)
        self.timeout = int(timeout)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _request_with_retries(self, url, *, params, max_retries=3):
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                if response.status_code == 429:
                    if attempt == max_retries - 1:
                        response.raise_for_status()
                    time.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                return response
            except requests.Timeout:
                # Timeout retry once for SPARQL as required.
                if attempt >= 1:
                    raise
                continue
        raise RuntimeError("Wikidata request retries exhausted")

    def resolve_entity(self, entity):
        params = {
            "action": "wbsearchentities",
            "search": entity,
            "language": "en",
            "format": "json",
            "limit": 1,
        }
        response = self._request_with_retries(WIKIDATA_SEARCH_URL, params=params)
        payload = response.json()
        result = (payload.get("search") or [None])[0]
        if not result:
            return None

        qid = result.get("id")
        label = result.get("label") or entity
        description = result.get("description") or ""
        return {
            "qid": qid,
            "label": label,
            "description": description,
            "wikidata_url": f"https://www.wikidata.org/wiki/{qid}",
        }

    def _predicate_property_ids(self, predicate_hint):
        text = (predicate_hint or "").lower().strip()
        matched = []
        for key, value in PREDICATE_TO_PROPERTY.items():
            if key in text:
                matched.append(value)

        if matched:
            return matched

        return list(PREDICATE_TO_PROPERTY.values())

    def _sparql_property_values(self, qid, property_id):
        query = f"""
        SELECT ?value ?valueLabel WHERE {{
          wd:{qid} wdt:{property_id} ?value .
          OPTIONAL {{
            ?value rdfs:label ?valueLabel .
            FILTER(LANG(?valueLabel) = \"en\")
          }}
        }}
        LIMIT 10
        """
        params = {"query": query, "format": "json"}
        response = self._request_with_retries(WIKIDATA_SPARQL_URL, params=params)
        rows = response.json().get("results", {}).get("bindings", [])

        values = []
        for row in rows:
            raw_value = row.get("valueLabel", {}).get("value") or row.get("value", {}).get("value")
            if raw_value:
                values.append(raw_value)

        deduped = []
        seen = set()
        for value in values:
            key = value.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(value)

        return deduped

    def lookup(self, entity, predicate_hint=""):
        cache_key = f"{(entity or '').strip().lower()}|{(predicate_hint or '').strip().lower()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        resolved = self.resolve_entity(entity)
        if not resolved:
            result = {
                "qid": "",
                "label": entity,
                "properties": {},
                "wikidata_url": "",
            }
            self.cache.set(cache_key, result)
            return result

        qid = resolved["qid"]
        properties = {}
        for property_id in self._predicate_property_ids(predicate_hint):
            prop_values = self._sparql_property_values(qid, property_id)
            if prop_values:
                properties[property_id] = prop_values

        result = {
            "qid": qid,
            "label": resolved["label"],
            "properties": properties,
            "wikidata_url": resolved["wikidata_url"],
        }
        self.cache.set(cache_key, result)
        return result


__all__ = ["WikidataClient", "PREDICATE_TO_PROPERTY"]
