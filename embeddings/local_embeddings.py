from sentence_transformers import SentenceTransformer
from typing import List

class LocalEmbeddings:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: List[str]):
        embs = self.model.encode(texts, batch_size=64, show_progress_bar=False, convert_to_numpy=True)
        return embs.tolist()

    def embed_query(self, text: str):
        em = self.model.encode([text], convert_to_numpy=True)
        return em[0].tolist()
