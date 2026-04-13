import re


ALLOWED_ENTITY_TYPES = {"PERSON", "ORG", "GPE", "DATE", "EVENT"}


class ClaimExtractor:
    def __init__(self):
        self._nlp = None

    def _load_nlp(self):
        if self._nlp is not None:
            return self._nlp

        try:
            import spacy

            self._nlp = spacy.load("en_core_web_sm")
        except Exception:
            self._nlp = False
        return self._nlp

    def _fallback_claims(self, article_text):
        sentence_split = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", article_text or "")
            if s.strip()
        ]
        claims = []
        for sentence in sentence_split[:5]:
            claims.append(
                {
                    "subject": "Unknown",
                    "predicate": "states",
                    "object": "Unknown",
                    "claim_text": sentence,
                    "entities": [],
                }
            )
        return claims

    def extract_entities_and_claims(self, article_text):
        nlp = self._load_nlp()
        if not nlp:
            return self._fallback_claims(article_text)

        doc = nlp(article_text or "")
        claims = []

        for sent in doc.sents:
            sentence_text = sent.text.strip()
            if not sentence_text:
                continue

            sent_entities = [
                {
                    "text": ent.text.strip(),
                    "label": ent.label_,
                    "start_char": ent.start_char,
                    "end_char": ent.end_char,
                }
                for ent in sent.ents
                if ent.label_ in ALLOWED_ENTITY_TYPES and ent.text.strip()
            ]

            if not sent_entities:
                continue

            sent_entities.sort(key=lambda item: item["start_char"])
            subject = sent_entities[0]["text"]

            if len(sent_entities) >= 2:
                obj = sent_entities[1]["text"]
                between = sentence_text
                try:
                    first = sentence_text.index(subject) + len(subject)
                    second = sentence_text.index(obj, first)
                    between = sentence_text[first:second].strip()
                except ValueError:
                    between = sentence_text

                predicate = re.sub(r"\s+", " ", between).strip(" ,:;-")
                if not predicate:
                    predicate = "related to"
            else:
                obj = "Unknown"
                predicate = "states"

            claims.append(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "claim_text": sentence_text,
                    "entities": sent_entities,
                }
            )

        if not claims:
            return self._fallback_claims(article_text)

        # De-duplicate by claim text while keeping ordering stable.
        deduped = []
        seen = set()
        for claim in claims:
            key = claim.get("claim_text", "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(claim)

        return deduped[:8]


__all__ = ["ClaimExtractor"]
