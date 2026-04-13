import re


class RelationExtractor:

    def __init__(self):
        self.nlp = self._load_nlp()

    def _load_nlp(self):
        try:
            import spacy

            return spacy.load("en_core_web_sm")
        except Exception:
            return None

    def extract(self, claim):
        if self.nlp is None:
            return self._fallback_extract(claim)

        doc = self.nlp(claim)

        subject = None
        relation = None
        obj = None
        root = None

        for token in doc:

            if token.dep_ == "nsubj":
                subject = " ".join(part.text for part in token.subtree)

            if token.dep_ == "ROOT":
                root = token
                relation = token.lemma_

            if token.dep_ in ["dobj", "pobj"]:
                obj = " ".join(part.text for part in token.subtree)

        if root is not None and root.lemma_ == "be":
            complement = next(
                (token for token in doc if token.dep_ in {"attr", "acomp", "oprd"}),
                None
            )

            if complement is not None:
                relation = complement.lemma_

                prep = next((child for child in complement.children if child.dep_ == "prep"), None)
                if prep is not None:
                    relation = f"{complement.lemma_} {prep.lemma_}"
                    pobj = next((child for child in prep.children if child.dep_ == "pobj"), None)
                    if pobj is not None:
                        obj = " ".join(part.text for part in pobj.subtree)

        return {
            "subject": subject,
            "relation": relation,
            "object": obj
        }

    def _fallback_extract(self, claim):
        text = (claim or "").strip()
        tokens = text.split()

        if not tokens:
            return {"subject": None, "relation": None, "object": None}

        subject = None
        relation = None
        obj = None

        # Build subject from leading title-case tokens.
        subject_tokens = []
        for token in tokens:
            cleaned = token.strip(".,!?;:'\"()[]{}")
            if cleaned and cleaned[0].isupper():
                subject_tokens.append(cleaned)
            else:
                break

        if subject_tokens:
            subject = " ".join(subject_tokens)

        lower_tokens = [re.sub(r"[^A-Za-z]", "", token).lower() for token in tokens]
        be_index = next((i for i, token in enumerate(lower_tokens) if token in {"is", "are", "was", "were"}), None)

        if be_index is not None:
            remaining = tokens[be_index + 1:]
            remaining_lower = [re.sub(r"[^A-Za-z]", "", token).lower() for token in remaining]

            if "of" in remaining_lower:
                of_index = remaining_lower.index("of")
                relation_tokens = [
                    re.sub(r"[^A-Za-z]", "", token).lower()
                    for token in remaining[:of_index]
                    if re.sub(r"[^A-Za-z]", "", token).lower() not in {"a", "an", "the"}
                ]
                object_tokens = [token.strip(".,!?;:'\"()[]{}") for token in remaining[of_index + 1:]]

                relation = " ".join(token for token in relation_tokens if token)
                if relation:
                    relation = f"{relation} of"
                obj = " ".join(token for token in object_tokens if token) or None

                return {
                    "subject": subject,
                    "relation": relation or None,
                    "object": obj
                }

            relation_tokens = [
                re.sub(r"[^A-Za-z]", "", token).lower()
                for token in remaining
                if re.sub(r"[^A-Za-z]", "", token).lower() not in {"a", "an", "the"}
            ]
            relation = next((token for token in relation_tokens if token), None)

            return {
                "subject": subject,
                "relation": relation,
                "object": None
            }

        # Pick relation as first alphabetic token after auxiliary verbs.
        auxiliaries = {"is", "are", "was", "were", "has", "have", "had", "will", "would", "did", "does", "do"}
        for token in tokens[len(subject_tokens):]:
            cleaned = re.sub(r"[^A-Za-z]", "", token).lower()
            if not cleaned or cleaned in auxiliaries:
                continue
            relation = cleaned
            break

        # Use remaining text as object candidate.
        if relation:
            rel_index = None
            for i, token in enumerate(tokens):
                cleaned = re.sub(r"[^A-Za-z]", "", token).lower()
                if cleaned == relation:
                    rel_index = i
                    break
            if rel_index is not None and rel_index + 1 < len(tokens):
                obj = " ".join(tokens[rel_index + 1:]).strip(" .,!?:;\"'")

        return {
            "subject": subject,
            "relation": relation,
            "object": obj or None
        }


__all__ = ["RelationExtractor"]