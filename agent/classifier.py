import numpy as np


class SimpleKNNClassifier:
    """
    Very small KNN classifier using the HuggingFaceEmbeddings interface.
    """

    def __init__(self, seed_examples: dict, emb_model):
        """
        seed_examples = {
            "insurance": ["what is insurance", "benefits", ...],
            "other": [...],
        }
        emb_model = HuggingFaceEmbeddings
        """

        self.emb_model = emb_model
        self.labels = []
        self.embeddings = []

        for label, examples in seed_examples.items():
            embs = emb_model.embed_documents(examples)
            for e in embs:
                self.labels.append(label)
                self.embeddings.append(e)

        self.embeddings = np.array(self.embeddings)

    def predict_topk(self, query: str, k=2):
        q_emb = np.array(self.emb_model.embed_query(query))

        sims = (self.embeddings @ q_emb) / (
            np.linalg.norm(self.embeddings, axis=1) * (np.linalg.norm(q_emb) + 1e-12)
        )

        ranked = sorted(
            zip(self.labels, sims.tolist()), key=lambda x: x[1], reverse=True
        )
        return ranked[:k]
