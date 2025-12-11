from sentence_transformers import SentenceTransformer

class LocalEmbeddings:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
    def embed(self, text):
        return self.model.encode([text], convert_to_numpy=True)[0].tolist()
