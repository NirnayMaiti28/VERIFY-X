from sentence_transformers import SentenceTransformer

class EmbeddingGenerator:

    def __init__(self):
        # Load pretrained embedding model
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def generate(self, text: str):
        """
        Generate embedding vector for input text
        """

        embedding = self.model.encode(text)

        return embedding