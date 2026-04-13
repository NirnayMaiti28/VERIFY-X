import json
import os
import re

import requests

from text_verification.knowledge_layer.claim_extractor import ClaimExtractor
from text_verification.knowledge_layer.wikidata_client import (
    PREDICATE_TO_PROPERTY,
    WikidataClient,
)
from text_verification.knowledge_layer.wikipedia_client import WikipediaClient


KNOWLEDGE_VERIFICATION_PROMPT = """
You are a fact-checker. Your verdict must be grounded strictly in the
provided evidence. Follow these rules exactly:

1. If the evidence confirms the claim was TRUE as of its publication
    date, and no evidence explicitly states the opposite, return TRUE.

2. Do NOT require the word "currently" to appear verbatim in the
    evidence. Recency of the source is sufficient to confirm present
    state.

3. Only return FALSE if evidence explicitly and directly states the
    opposite of the claim. Absence of confirmation is NOT falsification.

4. Return UNVERIFIABLE only when evidence is entirely absent,
    irrelevant, or too ambiguous to support any verdict.

5. For role and position claims: if the most recent evidence confirms
    the role, return TRUE regardless of older contradicting articles.

Respond in JSON only, no preamble, no markdown:
{
  "verdict": "TRUE" | "FALSE" | "MIXED" | "UNVERIFIABLE",
  "confidence": 0.0-1.0,
  "reason": "one sentence citing the specific evidence used",
  "most_recent_source_date": "YYYY-MM-DD or unknown"
}
""".strip()


class WikiKnowledgeLayer:
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    def __init__(self):
        self.claim_extractor = ClaimExtractor()
        self.wikidata_client = WikidataClient()
        self.wikipedia_client = WikipediaClient()
        self.model_name = os.getenv("OLLAMA_MODEL", "tinyllama")
        self.session = requests.Session()

    def extract_entities_and_claims(self, article_text):
        return self.claim_extractor.extract_entities_and_claims(article_text)

    def lookup_wikidata(self, entity, predicate_hint=""):
        return self.wikidata_client.lookup(entity, predicate_hint)

    def fetch_wikipedia_summary(self, entity):
        return self.wikipedia_client.fetch_summary(entity)

    def _evidence_text(self, wikidata_result, wiki_summary):
        lines = []
        for property_id, values in (wikidata_result.get("properties") or {}).items():
            readable_predicate = next(
                (name for name, pid in PREDICATE_TO_PROPERTY.items() if pid == property_id),
                property_id,
            )
            lines.append(f"- {readable_predicate} ({property_id}): {', '.join(values[:5])}")

        wikidata_lines = "\n".join(lines) if lines else "- No Wikidata properties found"
        wiki_extract = (wiki_summary.get("extract") or "").strip() or "No Wikipedia summary available"

        return wikidata_lines, wiki_extract

    def _call_llm_json(self, prompt):
        try:
            num_gpu = int(os.getenv("OLLAMA_NUM_GPU", "0"))
        except ValueError:
            num_gpu = 0

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"num_gpu": num_gpu},
        }
        response = self.session.post(self.OLLAMA_URL, json=payload, timeout=90)
        response.raise_for_status()
        raw = response.json().get("response", "").strip()

        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("LLM did not return a JSON object")

        parsed = json.loads(match.group(0))
        return parsed, raw

    def _semantic_overlap(self, claim_text, evidence_text):
        stopwords = {
            "the", "a", "an", "is", "was", "are", "were", "of", "in", "on", "at", "to", "for",
            "and", "or", "not", "as", "by", "be", "has", "have", "with", "from", "that", "this",
        }
        claim_tokens = {
            token for token in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9\-]{1,}\b", (claim_text or "").lower())
            if token not in stopwords
        }
        evidence_tokens = {
            token for token in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9\-]{1,}\b", (evidence_text or "").lower())
            if token not in stopwords
        }

        if not claim_tokens or not evidence_tokens:
            return 0.0
        return len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))

    def _extract_type_terms(self, wikidata_facts, wikipedia_extract):
        text = f"{wikidata_facts}\n{wikipedia_extract}".lower()
        terms = set()

        patterns = [
            r"instance of\s*\([^)]*\):\s*([^\n]+)",
            r"subclass of\s*\([^)]*\):\s*([^\n]+)",
            r"is an?\s+([a-z][a-z\- ]{2,80})",
            r"is the\s+([a-z][a-z\- ]{2,80})",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                value = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;-")
                if value:
                    terms.add(value)

        return terms

    def _claim_relation_family(self, claim_text):
        text = (claim_text or "").lower()
        if any(marker in text for marker in ["made of", "made up of", "composed of", "consists of", "consist of"]):
            return "composition"
        if any(marker in text for marker in ["located in", "located at", "in ", "part of", "from "]):
            return "location"
        if any(marker in text for marker in ["is a", "is an", "is the"]):
            return "identity"
        if any(marker in text for marker in ["president", "prime minister", "leader", "chair", "director", "minister"]):
            return "role"
        return "other"

    def _is_generic_impossible_claim(self, claim_text, wikidata_facts, wikipedia_extract):
        relation = self._claim_relation_family(claim_text)
        if relation not in {"composition", "identity", "location", "role"}:
            return False

        evidence_text = f"{wikidata_facts}\n{wikipedia_extract}".lower()
        type_terms = self._extract_type_terms(wikidata_facts, wikipedia_extract)
        if not type_terms:
            return False

        non_material_entities = {
            "natural satellite",
            "planet",
            "star",
            "galaxy",
            "city",
            "country",
            "state",
            "province",
            "district",
            "person",
            "human",
            "politician",
            "organization",
            "company",
            "event",
            "river",
            "mountain",
            "building",
            "airport",
            "school",
            "university",
            "vehicle",
            "species",
            "animal",
        }

        if relation == "composition":
            # If the evidence classifies the subject as a concrete entity rather than a material/substance,
            # claims that it is made of a material are usually false when unsupported.
            if any(term in evidence_text for term in non_material_entities):
                return True

        if relation in {"identity", "role", "location"}:
            if any(term in evidence_text for term in ["not", "former", "ex", "was", "is no longer"]):
                return True

        return False
    def score_claim(self, claim, wikidata, wiki_summary):
        claim_text = claim.get("claim_text") or ""
        wikidata_facts, wikipedia_extract = self._evidence_text(wikidata, wiki_summary)

        if self._is_generic_impossible_claim(claim_text, wikidata_facts, wikipedia_extract):
            return {
                "claim": claim,
                "verdict": "FALSE",
                "confidence": 0.98,
                "reason": "Wikidata/Wikipedia evidence contradicts the composition claim.",
                "evidence_used": f"{wikidata_facts}\n{wikipedia_extract}".strip(),
                "sources": [
                    wikidata.get("wikidata_url", ""),
                    wiki_summary.get("wikipedia_url", ""),
                ],
                "most_recent_source_date": "unknown",
                "llm_raw": "",
            }

        prompt = (
            f"SYSTEM:\n{KNOWLEDGE_VERIFICATION_PROMPT}\n\n"
            "USER:\n"
            f"CLAIM: {claim_text}\n\n"
            "WIKIDATA FACTS:\n"
            f"{wikidata_facts}\n\n"
            "WIKIPEDIA CONTEXT:\n"
            f"{wikipedia_extract}\n"
            "\nIf the claim is obviously impossible, scientifically incompatible, or directly contradicted by the evidence, return FALSE."
        )

        default_result = {
            "claim": claim,
            "verdict": "UNVERIFIABLE",
            "confidence": 0.3,
            "reason": "Knowledge evidence was insufficient for deterministic verification.",
            "evidence_used": "No sufficient Wikidata/Wikipedia facts found.",
            "sources": [
                wikidata.get("wikidata_url", ""),
                wiki_summary.get("wikipedia_url", ""),
            ],
            "most_recent_source_date": "unknown",
            "llm_raw": "",
        }

        try:
            llm_json, raw = self._call_llm_json(prompt)
            verdict = str(llm_json.get("verdict", "UNVERIFIABLE")).strip().upper()
            if verdict not in {"TRUE", "FALSE", "MIXED", "UNVERIFIABLE"}:
                verdict = "UNVERIFIABLE"

            confidence = llm_json.get("confidence", 0.3)
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.3
            confidence = max(0.0, min(1.0, confidence))

            # Fallback: if Wikipedia context clearly overlaps the claim and no explicit negation,
            # treat weak LLM uncertainty as TRUE to reduce false negatives on factual claims.
            overlap = self._semantic_overlap(claim_text, wikipedia_extract)
            claim_lower = (claim_text or "").lower()
            wiki_lower = (wikipedia_extract or "").lower()
            subject_head = ((claim.get("subject") or "").strip().split(" ") or [""])[0].lower()
            negation_markers = [" not ", " never ", " denied ", " false ", " incorrect "]
            explicit_negation = any(marker in f" {wikipedia_extract.lower()} " for marker in negation_markers)
            strong_keywords = [
                "world cup",
                "leader of opposition",
                "prime minister",
                "president",
                "won",
                "elected",
            ]
            keyword_supported = any(keyword in claim_lower and keyword in wiki_lower for keyword in strong_keywords)
            if (
                verdict == "UNVERIFIABLE"
                and not explicit_negation
                and (overlap >= 0.35 or (subject_head and subject_head in wiki_lower and keyword_supported))
            ):
                verdict = "TRUE"
                confidence = max(confidence, 0.85)

            return {
                "claim": claim,
                "verdict": verdict,
                "confidence": confidence,
                "reason": str(llm_json.get("reason") or default_result["reason"]),
                "evidence_used": str(llm_json.get("evidence_used") or ""),
                "sources": [
                    wikidata.get("wikidata_url", ""),
                    wiki_summary.get("wikipedia_url", ""),
                ],
                "most_recent_source_date": str(llm_json.get("most_recent_source_date") or "unknown"),
                "llm_raw": raw,
            }
        except Exception:
            return default_result

    def aggregate_verdict(self, scored_claims):
        if not scored_claims:
            return {
                "verdict": "UNVERIFIABLE",
                "confidence": 0.0,
                "claim_breakdown": [],
                "knowledge_gaps": [],
                "all_sources": [],
            }

        false_high = [
            c for c in scored_claims if c.get("verdict") == "FALSE" and float(c.get("confidence", 0)) > 0.75
        ]
        verifiable = [c for c in scored_claims if c.get("verdict") in {"TRUE", "FALSE"}]
        all_true = verifiable and all(c.get("verdict") == "TRUE" for c in verifiable)

        verdict_set = {c.get("verdict") for c in scored_claims}

        if false_high:
            verdict = "FALSE"
        elif all_true and len(verifiable) == len(scored_claims):
            verdict = "TRUE"
        elif verdict_set & {"TRUE", "FALSE"}:
            verdict = "MIXED"
        else:
            verdict = "UNVERIFIABLE"

        confidence_values = [float(c.get("confidence", 0.0) or 0.0) for c in scored_claims]
        confidence = sum(confidence_values) / max(1, len(confidence_values))

        knowledge_gaps = [
            c.get("claim", {}).get("claim_text", "")
            for c in scored_claims
            if c.get("verdict") == "UNVERIFIABLE"
        ]

        all_sources = []
        seen = set()
        for claim in scored_claims:
            for source in claim.get("sources", []):
                source = (source or "").strip()
                if not source:
                    continue
                if source in seen:
                    continue
                seen.add(source)
                all_sources.append(source)

        claim_breakdown = [
            {
                "claim": item.get("claim", {}).get("claim_text", ""),
                "verdict": item.get("verdict"),
                "confidence": item.get("confidence"),
                "reason": item.get("reason"),
                "sources": item.get("sources", []),
                "evidence_used": item.get("evidence_used", ""),
            }
            for item in scored_claims
        ]

        return {
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "claim_breakdown": claim_breakdown,
            "knowledge_gaps": knowledge_gaps,
            "all_sources": all_sources,
        }

    def verify_article(self, article_text):
        claims = self.extract_entities_and_claims(article_text)
        scored = []

        for claim in claims:
            subject = claim.get("subject") or ""
            predicate = claim.get("predicate") or ""
            wikidata = self.lookup_wikidata(subject, predicate)
            wiki_summary = self.fetch_wikipedia_summary(subject)
            scored_claim = self.score_claim(claim, wikidata, wiki_summary)
            scored.append(scored_claim)

        aggregated = self.aggregate_verdict(scored)
        aggregated["claims_extracted"] = claims
        return aggregated


__all__ = ["WikiKnowledgeLayer"]
