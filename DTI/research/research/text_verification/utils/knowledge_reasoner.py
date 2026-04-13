import re
import time

import numpy as np
import requests

from text_verification.utils.relation_extractor import RelationExtractor
from text_verification.utils.wikipedia_property_search import WikidataPropertySearch


class KnowledgeReasoner:
    """Knowledge reasoning with structured contradiction and support detection."""

    WIKIDATA_API = "https://www.wikidata.org/w/api.php"
    HEADERS = {
        "User-Agent": "text-verification-research/1.0 (local development)"
    }
    _RELATION_STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "in", "on", "at", "to", "of", "for", "by", "with", "and", "or",
        "that", "this", "it", "as", "from", "into", "about", "over", "under",
    }

    def __init__(self):
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self.model = None

        self.relation_extractor = RelationExtractor()
        self.property_search = WikidataPropertySearch()
        self._entity_search_cache = {}
        self._entity_bundle_cache = {}
        self._entity_label_cache = {}

    def _get_json(self, params, retries=2):
        for attempt in range(retries + 1):
            try:
                response = requests.get(
                    self.WIKIDATA_API,
                    params=params,
                    headers=self.HEADERS,
                    timeout=5,
                )
                response.raise_for_status()
                return response.json()
            except Exception:
                if attempt == retries:
                    return None
                time.sleep(0.3 * (attempt + 1))

    def _normalize_entity_name(self, value):
        text = (value or "").strip()
        text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _clean_text(self, value):
        text = (value or "").strip().lower()
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _split_sentences(self, text):
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        if not cleaned:
            return []

        chunks = re.split(r"(?<=[.!?])\s+", cleaned)
        return [chunk.strip() for chunk in chunks if len(chunk.strip()) >= 25]

    def _salient_tokens(self, text):
        tokens = []
        for raw in re.findall(r"\b[a-zA-Z0-9][a-zA-Z0-9\-\.]{1,}\b", text or ""):
            token = raw.lower().strip("-.")
            if len(token) < 3:
                continue
            if token in self._RELATION_STOPWORDS:
                continue
            tokens.append(token)
        return tokens

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

        if not claim_tokens:
            return 0.0

        overlap = len(claim_tokens & sentence_tokens)
        return overlap / len(claim_tokens)

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

    def _claim_numbers(self, text):
        return {value for value in re.findall(r"\b\d+(?:\.\d+)?\b", text or "")}

    def _numbers_compatible(self, left_numbers, right_numbers):
        if not left_numbers or not right_numbers:
            return True

        left_vals = []
        right_vals = []

        for value in left_numbers:
            try:
                left_vals.append(float(value))
            except Exception:
                continue

        for value in right_numbers:
            try:
                right_vals.append(float(value))
            except Exception:
                continue

        if not left_vals or not right_vals:
            return True

        # Treat near-equal numeric mentions as compatible (e.g. 365 vs 365.25).
        for left in left_vals:
            for right in right_vals:
                if abs(left - right) <= 0.5:
                    return True

        return False

    def _is_year_like(self, value):
        try:
            number = int(float(str(value)))
        except Exception:
            return False
        return 1000 <= number <= 2100

    def _relation_overlap(self, claim, sentence):
        claim_tokens = set(self._salient_tokens(claim))
        sentence_tokens = set(self._salient_tokens(sentence))

        if not claim_tokens or not sentence_tokens:
            return 0.0

        overlap = len(claim_tokens & sentence_tokens)
        return overlap / max(1, len(claim_tokens))

    def _specific_overlap_count(self, claim, sentence):
        claim_tokens = set(self._salient_tokens(claim))
        sentence_tokens = set(self._salient_tokens(sentence))
        return len(claim_tokens & sentence_tokens)

    def _is_negated(self, text):
        lowered = f" {(text or '').lower()} "
        tokens = (" not ", " never ", " no ", "n't", " without ")
        return any(token in lowered for token in tokens)

    def _relation_object_phrase(self, text):
        lowered = (text or "").lower()
        patterns = [
            r"\blocated in\s+([a-z][a-z\s\-]{1,80})",
            r"\bheld in\s+([a-z][a-z\s\-]{1,80})",
            r"\bis in\s+([a-z][a-z\s\-]{1,80})",
            r"\bon\s+([a-z][a-z\s\-]{1,80})",
            r"\breleased\s+([a-z0-9][a-z0-9\s\-\.]{1,80})",
            r"\blaunch(?:ed)?\s+([a-z0-9][a-z0-9\s\-\.]{1,80})",
            r"\bfrom\s+([a-z][a-z\s\-]{1,80})",
            r"\bcapital of\s+([a-z][a-z\s\-]{1,80})",
            r"\bjoined\s+([a-z][a-z\s\-]{1,80})",
            r"\bmember of\s+([a-z][a-z\s\-]{1,80})",
            r"\baffiliated with\s+([a-z][a-z\s\-]{1,80})",
        ]

        for pattern in patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue

            phrase = re.sub(r"[^a-z\s\-]", "", match.group(1)).strip()
            phrase = re.sub(r"\b(in|on|at|during)\s+\d{4}\b", "", phrase).strip()
            phrase = re.sub(r"\s+", " ", phrase)
            if phrase:
                return phrase

        return ""

    def _extract_years(self, text):
        values = set()
        for token in self._claim_numbers(text):
            if self._is_year_like(token):
                values.add(str(int(float(token))))
        return values

    def _has_contradiction(self, claim, best_sentence):
        if not best_sentence:
            return False

        overlap_count = self._specific_overlap_count(claim, best_sentence)

        claim_negated = self._is_negated(claim)
        sentence_negated = self._is_negated(best_sentence)
        if claim_negated != sentence_negated:
            return True

        claim_numbers = self._claim_numbers(claim)
        sentence_numbers = self._claim_numbers(best_sentence)
        relation_overlap = self._relation_overlap(claim, best_sentence)

        claim_has_year = any(self._is_year_like(value) for value in claim_numbers)
        sentence_has_year = any(self._is_year_like(value) for value in sentence_numbers)

        numeric_conflict_reliable = (
            claim_has_year
            and sentence_has_year
            and len(claim_numbers) == 1
            and len(sentence_numbers) == 1
            and relation_overlap >= 0.5
        )

        if (
            claim_numbers
            and sentence_numbers
            and not self._numbers_compatible(claim_numbers, sentence_numbers)
            and overlap_count >= 2
            and numeric_conflict_reliable
        ):
            return True

        claim_object = self._relation_object_phrase(claim)
        sentence_object = self._relation_object_phrase(best_sentence)

        if claim_object and sentence_object and claim_object != sentence_object:
            return True

        return False

    def _relation_candidates(self, relation):
        rel = self._clean_text(relation)
        if not rel:
            return []

        candidates = [rel]
        words = rel.split()

        if words:
            stemmed = []
            for word in words:
                if word.endswith("ing") and len(word) > 5:
                    stemmed.append(word[:-3])
                elif word.endswith("ed") and len(word) > 4:
                    stemmed.append(word[:-2])
                elif word.endswith("es") and len(word) > 4:
                    stemmed.append(word[:-2])
                elif word.endswith("s") and len(word) > 3:
                    stemmed.append(word[:-1])
                else:
                    stemmed.append(word)

            normalized = " ".join(stemmed).strip()
            if normalized and normalized not in candidates:
                candidates.append(normalized)

        if len(words) > 1:
            head = words[0]
            if head not in candidates:
                candidates.append(head)

        return candidates

    def _relation_property_ids(self, relation):
        ids = []

        for candidate in self._relation_candidates(relation):
            property_id = self.property_search.search_property(candidate)
            if property_id:
                ids.append(property_id)

        unique = []
        seen = set()
        for item in ids:
            if item not in seen:
                seen.add(item)
                unique.append(item)

        return unique

    def _search_entity(self, name):
        normalized = self._normalize_entity_name(name)
        if not normalized:
            return None

        key = normalized.lower()
        if key in self._entity_search_cache:
            return self._entity_search_cache[key]

        params = {
            "action": "wbsearchentities",
            "search": normalized,
            "language": "en",
            "format": "json",
        }

        data = self._get_json(params)
        entity_id = None

        if data and data.get("search"):
            entity_id = data["search"][0].get("id")

        self._entity_search_cache[key] = entity_id
        return entity_id

    def _get_entity_bundle(self, entity_id):
        if not entity_id:
            return None

        if entity_id in self._entity_bundle_cache:
            return self._entity_bundle_cache[entity_id]

        params = {
            "action": "wbgetentities",
            "ids": entity_id,
            "format": "json",
            "props": "labels|claims",
        }

        data = self._get_json(params)
        bundle = None

        try:
            bundle = data["entities"][entity_id]
        except Exception:
            bundle = None

        self._entity_bundle_cache[entity_id] = bundle
        return bundle

    def _get_entity_label(self, entity_id):
        if not entity_id:
            return ""

        if entity_id in self._entity_label_cache:
            return self._entity_label_cache[entity_id]

        bundle = self._get_entity_bundle(entity_id)
        label = ""

        try:
            label = bundle["labels"]["en"]["value"]
        except Exception:
            label = ""

        self._entity_label_cache[entity_id] = label
        return label

    def _statement_object_label(self, statement):
        mainsnak = statement.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value")

        if isinstance(value, dict):
            if value.get("id"):
                return self._get_entity_label(value.get("id"))

            if value.get("text"):
                return str(value.get("text"))

            if value.get("amount") is not None:
                try:
                    return str(int(float(str(value.get("amount")).lstrip("+"))))
                except Exception:
                    return str(value.get("amount"))

            if value.get("time"):
                return str(value.get("time"))

        if isinstance(value, str):
            return value

        return ""

    def _facts_from_wikidata(self, subject, relation):
        subject_id = self._search_entity(subject)
        if not subject_id:
            return []

        bundle = self._get_entity_bundle(subject_id)
        if not bundle:
            return []

        claims = bundle.get("claims", {})
        property_ids = self._relation_property_ids(relation)
        if not property_ids:
            return []

        facts = []

        for property_id in property_ids:
            for statement in claims.get(property_id, []) or []:
                object_label = self._statement_object_label(statement)
                if object_label:
                    facts.append({
                        "property_id": property_id,
                        "object": object_label,
                    })

        return facts

    def _token_match(self, expected, actual):
        left = self._clean_text(expected)
        right = self._clean_text(actual)

        if not left or not right:
            return False

        if left == right:
            return True

        if left in right or right in left:
            return True

        left_tokens = [token for token in left.split() if token]
        right_tokens = [token for token in right.split() if token]

        if left_tokens and right_tokens:
            left_set = set(left_tokens)
            right_set = set(right_tokens)
            overlap = len(left_set & right_set)

            if overlap > 0 and (overlap / max(1, len(left_set))) >= 0.6:
                return True

            left_initials = "".join(token[0] for token in left_tokens if token)
            right_initials = "".join(token[0] for token in right_tokens if token)

            if left == right_initials or right == left_initials:
                return True

        return False

    def _triple_from_claim(self, claim, entities, main_entity=""):
        triple = self.relation_extractor.extract(claim) or {}

        subject = (triple.get("subject") or "").strip()
        relation = (triple.get("relation") or "").strip()
        obj = (triple.get("object") or "").strip()

        if not subject:
            subject = (main_entity or "").strip()

        if not subject and entities:
            subject = (entities[0].get("text") or "").strip()

        return {
            "subject": subject,
            "relation": relation,
            "object": obj,
        }

    def _structured_signal(self, triple):
        subject = triple.get("subject")
        relation = triple.get("relation")
        obj = triple.get("object")

        if not subject or not relation:
            return None

        facts = self._facts_from_wikidata(subject, relation)
        if not facts:
            return None

        if not obj:
            relation_strength = min(1.0, len(facts) / 4.0)
            return {
                "support": True,
                "contradiction": False,
                "K_score": 0.55 + (0.25 * relation_strength),
                "fact": facts[0],
                "facts": facts[:5],
                "reason": f"Wikidata stores relation {relation} for {subject}.",
            }

        for fact in facts:
            if self._token_match(obj, fact.get("object", "")):
                relation_strength = min(1.0, len(facts) / 4.0)
                return {
                    "support": True,
                    "contradiction": False,
                    "K_score": 0.7 + (0.25 * relation_strength),
                    "fact": fact,
                    "facts": facts[:5],
                    "reason": (
                        f"Known fact for {subject} has {relation} -> {fact.get('object')}, "
                        f"which matches the claim."
                    ),
                }

        claim_years = self._extract_years(obj)
        fact_years = set()
        for fact in facts:
            fact_years.update(self._extract_years(fact.get("object", "")))

        if claim_years and fact_years and claim_years.isdisjoint(fact_years):
            return {
                "support": False,
                "contradiction": True,
                "K_score": -0.8,
                "fact": facts[0],
                "facts": facts[:5],
                "reason": (
                    f"Known facts for {subject} indicate years {sorted(fact_years)}, "
                    f"which conflict with claimed year(s) {sorted(claim_years)}."
                ),
            }

        relation_strength = min(1.0, len(facts) / 4.0)
        return {
            "support": False,
            "contradiction": False,
            "K_score": -0.15,
            "fact": facts[0],
            "facts": facts[:5],
            "reason": (
                f"Known relation {relation} exists for {subject}, but no close object match "
                f"was found for '{obj}'."
            ),
        }

    def _sentences_from_pages(self, wiki_pages):
        candidates = []

        for page in wiki_pages or []:
            title = (page.get("title") or "").strip()
            content = page.get("content") or ""

            for item in page.get("top_sentences", []) or []:
                text = (item.get("text") or "").strip()
                if text:
                    candidates.append({
                        "text": text,
                        "title": title,
                    })

            # Use only the lead section from long pages to reduce off-topic drift.
            for sentence in self._split_sentences(content)[:12]:
                candidates.append({
                    "text": sentence,
                    "title": title,
                })

        unique = []
        seen = set()

        for item in candidates:
            text = item["text"]
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique

    def _semantic_signal(self, claim, sentences):
        if not sentences:
            return None

        sentence_texts = [item["text"] for item in sentences]
        similarities = self._semantic_similarity(claim, sentence_texts)

        if not similarities:
            return None

        weighted_scores = []
        for idx, sim in enumerate(similarities):
            sentence = sentence_texts[idx]
            overlap = self._relation_overlap(claim, sentence)
            weighted_scores.append((0.75 * float(sim)) + (0.25 * float(overlap)))

        best_idx = int(np.argmax(weighted_scores))
        best_similarity = float(max(0.0, min(1.0, similarities[best_idx])))
        best_sentence = sentence_texts[best_idx]
        best_title = sentences[best_idx].get("title", "")
        relation_overlap = self._relation_overlap(claim, best_sentence)
        overlap_count = self._specific_overlap_count(claim, best_sentence)
        relation_weak = relation_overlap < 0.22 or overlap_count < 2

        contradiction = self._has_contradiction(claim, best_sentence)
        if relation_weak:
            contradiction = False

        if contradiction:
            claim_obj = self._relation_object_phrase(claim)
            sent_obj = self._relation_object_phrase(best_sentence)

            if claim_obj and sent_obj and claim_obj != sent_obj:
                k_score = -(0.45 + (0.45 * best_similarity))
            else:
                k_score = -(0.35 + (0.55 * best_similarity))
        else:
            k_score = 0.25 + (0.75 * best_similarity)

        # Scale confidence by relation overlap so generic same-entity sentences do not dominate.
        overlap_scale = 0.5 + (0.8 * min(1.0, relation_overlap))
        k_score *= overlap_scale

        # If sentence matches entity words but not the relation, avoid strong verdicts.
        if relation_weak:
            k_score = min(k_score, 0.35)

        # Moderate overlap should not produce very strong confidence.
        if 0.22 <= relation_overlap < 0.35:
            k_score = max(-0.6, min(0.6, k_score))

        return {
            "K_score": float(k_score),
            "similarity": round(best_similarity, 4),
            "relation_overlap": round(relation_overlap, 4),
            "contradiction": contradiction,
            "best_sentence": best_sentence,
            "best_title": best_title,
        }

    def reason(self, claim, entities, wiki_pages=None, main_entity=""):
        triple = self._triple_from_claim(claim, entities, main_entity=main_entity)
        structured = self._structured_signal(triple)

        sentences = self._sentences_from_pages(wiki_pages)
        semantic = self._semantic_signal(claim, sentences)

        selected_k = 0.0
        explanation = "No strong knowledge grounding was found."
        contradiction = False
        best_sentence = ""
        best_title = ""
        similarity = 0.0

        if structured is not None:
            selected_k = float(structured.get("K_score", 0.0) or 0.0)
            explanation = structured.get("reason") or explanation
            contradiction = bool(structured.get("contradiction", False))

        if semantic is not None:
            similarity = float(semantic.get("similarity", 0.0) or 0.0)
            best_sentence = semantic.get("best_sentence") or ""
            best_title = semantic.get("best_title") or ""

            if structured is None:
                selected_k = float(semantic.get("K_score", 0.0) or 0.0)
                contradiction = bool(semantic.get("contradiction", False))
                explanation = (
                    f"Best encyclopedic sentence from {best_title or 'Wikipedia'} "
                    f"matched with similarity {similarity:.2f}."
                )

                claim_years = self._extract_years(claim)
                sentence_years = self._extract_years(best_sentence)

                if claim_years and sentence_years and claim_years.isdisjoint(sentence_years):
                    selected_k = min(selected_k, -0.78)
                    contradiction = True
                    explanation = (
                        f"Best encyclopedic sentence from {best_title or 'Wikipedia'} "
                        f"contains conflicting year(s) {sorted(sentence_years)} "
                        f"for claimed year(s) {sorted(claim_years)}."
                    )
                elif claim_years and not sentence_years:
                    # Missing temporal grounding must not produce a strong TRUE for year-specific claims.
                    selected_k = min(selected_k, 0.35)

        selected_k = max(-0.9, min(1.0, selected_k))

        strong_signal = False
        if structured is not None:
            strong_signal = abs(selected_k) > 0.7
        elif semantic is not None:
            sem_overlap = float(semantic.get("relation_overlap", 0.0) or 0.0)
            sem_similarity = float(semantic.get("similarity", 0.0) or 0.0)
            sem_contradiction = bool(semantic.get("contradiction", False))

            if not sem_contradiction:
                strong_signal = (
                    selected_k >= 0.72
                    and sem_overlap >= 0.35
                    and sem_similarity >= 0.72
                )
            else:
                strong_signal = (
                    selected_k <= -0.72
                    and sem_overlap >= 0.5
                    and sem_similarity >= 0.75
                )

        verdict = "UNCERTAIN"
        if selected_k >= 0.7:
            verdict = "TRUE"
        elif selected_k <= -0.7:
            verdict = "FALSE"

        return {
            "verdict": verdict,
            "confidence": round(abs(selected_k), 3),
            "K_score": round(selected_k, 4),
            "entity": main_entity or triple.get("subject") or (entities[0].get("text") if entities else ""),
            "triple": triple,
            "best_match_sentence": best_sentence,
            "best_match_title": best_title,
            "similarity": round(similarity, 4),
            "contradiction": contradiction,
            "structured_signal": structured,
            "semantic_signal": semantic,
            "strong_signal": strong_signal,
            "explanation": explanation,
        }


__all__ = ["KnowledgeReasoner"]
