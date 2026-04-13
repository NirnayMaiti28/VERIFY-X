class ClaimNormalizer:

    def __init__(self):
        self.model = None
        self.np = None
        self.cosine_similarity = None

        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            from sentence_transformers import SentenceTransformer

            self.np = np
            self.cosine_similarity = cosine_similarity
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            self.model = None

        # store previous claim embeddings
        self.claim_memory = []

        self.threshold = 0.9

    def normalize(self, claim):
        claim = (claim or "").strip()

        if self.model is None:
            return claim

        embedding = self.model.encode([claim])[0]

        if len(self.claim_memory) == 0:
            self.claim_memory.append((claim, embedding))
            return claim

        if self.np is None or self.cosine_similarity is None:
            return claim

        stored_embeddings = self.np.array([c[1] for c in self.claim_memory])

        similarity = self.cosine_similarity([embedding], stored_embeddings)[0]

        max_index = similarity.argmax()
        max_score = similarity[max_index]

        if max_score > self.threshold:
            # return existing normalized claim
            return self.claim_memory[max_index][0]

        else:
            self.claim_memory.append((claim, embedding))
            return claim