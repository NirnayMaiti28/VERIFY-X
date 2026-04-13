import re


class EntityExtractor:

    _NOISY_ENTITY_LABELS = {
        "CARDINAL", "ORDINAL", "DATE", "TIME", "MONEY", "PERCENT", "QUANTITY"
    }
    _PERSON_MISLABEL_TERMS = {
        "moon", "mars", "earth", "venus", "mercury", "jupiter", "saturn", "uranus", "neptune"
    }

    def _is_useful_entity(self, text, label):
        value = (text or "").strip()
        tag = (label or "").upper()

        if not value:
            return False

        # Ignore pure number/date-like fragments as entity anchors.
        stripped = value.replace(",", "").replace(".", "")
        if stripped.isdigit():
            return False

        if tag in self._NOISY_ENTITY_LABELS:
            return False

        if tag == "PERSON" and value.lower() in self._PERSON_MISLABEL_TERMS:
            return False

        return True

    def __init__(self):
        self.nlp = self._load_nlp()

    def _load_nlp(self):
        # Try to ensure the small English NER model is available before giving up.
        try:
            import spacy
            from spacy.cli import download as spacy_download

            try:
                return spacy.load("en_core_web_sm")
            except OSError:
                spacy_download("en_core_web_sm")
                return spacy.load("en_core_web_sm")
        except Exception:
            return None

    def extract_entities(self, text: str):
        """
        Extract named entities from the claim
        """

        if self.nlp is None:
            return self._fallback_entities(text)

        doc = self.nlp(text)

        entities = []

        for ent in doc.ents:
            if not self._is_useful_entity(ent.text, ent.label_):
                continue

            entities.append({
                "text": ent.text,
                "label": ent.label_
            })

        if entities:
            return entities

        return self._fallback_entities(text)

    def extract_main_entity(self, text: str, entities=None):
        """Return the best single entity to anchor knowledge retrieval."""

        mission_like = re.findall(r"\b[A-Za-z]+-\d+[A-Za-z0-9\-]*\b", text or "")
        if mission_like:
            return mission_like[0]

        event_like = re.findall(r"\b(?=\w*[A-Za-z])(?=\w*\d)[A-Za-z0-9\-]{3,}\b", text or "")
        if event_like:
            return event_like[0]

        candidates = entities if entities is not None else self.extract_entities(text)
        candidates = [
            entity for entity in candidates
            if self._is_useful_entity(entity.get("text", ""), entity.get("label", ""))
        ]

        if not candidates:
            return ""

        label_priority = {
            "PERSON": 5,
            "ORG": 4,
            "GPE": 4,
            "LOC": 3,
            "NORP": 3,
            "FAC": 2,
            "EVENT": 2,
            "PRODUCT": 2,
            "WORK_OF_ART": 1,
        }

        best_entity = ""
        best_score = -1
        source_text = (text or "").lower()
        has_specific_label = any(
            (entity.get("label") or "").upper() in {"EVENT", "PRODUCT", "WORK_OF_ART", "FAC"}
            for entity in candidates
        )

        for idx, entity in enumerate(candidates):
            text_value = (entity.get("text") or "").strip()
            if not text_value:
                continue

            label = (entity.get("label") or "").upper()
            score = label_priority.get(label, 1) * 100
            score += min(30, len(text_value))
            score -= idx

            # Prefer specific named assets/events (e.g., "Chandrayaan-3", "GPT-4o").
            if any(ch.isdigit() for ch in text_value) or "-" in text_value:
                score += 90

            if len(text_value.split()) >= 2:
                score += 20

            # Slight position preference, but do not let first generic location always win.
            pos = source_text.find(text_value.lower()) if source_text else -1
            if pos >= 0:
                score += max(0, 25 - min(25, pos // 4))

            if has_specific_label and label == "GPE":
                score -= 40

            if score > best_score:
                best_score = score
                best_entity = text_value

        return best_entity

    def _fallback_entities(self, text: str):
        entities = []
        seen = set()

        for token in (text or "").split():
            normalized = token.strip(".,!?;:'\"()[]{}")

            if not normalized or normalized.lower() in {"is", "was", "dead", "alive", "deceased", "the", "a", "an"}:
                continue

            if not normalized[0].isupper():
                continue

            key = normalized.lower()
            if key in seen:
                continue

            seen.add(key)
            entities.append({
                "text": normalized,
                "label": "PERSON"
            })

        return entities


__all__ = ["EntityExtractor"]