import numpy as np
from embeddings.local_embeddings import LocalEmbeddings

class SimpleKNNClassifier:
    def __init__(self, mapping, emb_model: LocalEmbeddings):
        self.labels = list(mapping.keys())
        self.examples = [e for arr in mapping.values() for e in arr]
        self.example_labels = [lbl for lbl, arr in mapping.items() for _ in arr]
        self.emb = emb_model
        self.example_embs = self.emb.model.encode(self.examples, convert_to_numpy=True)

    def predict(self, text, k=2):
        q = self.emb.model.encode([text], convert_to_numpy=True)[0]
        sims = (self.example_embs @ q) / (np.linalg.norm(self.example_embs, axis=1) * (np.linalg.norm(q)+1e-12))
        scores = {}
        for lbl, sim in zip(self.example_labels, sims):
            scores.setdefault(lbl, []).append(sim)
        avg = {lbl: sum(v)/len(v) for lbl, v in scores.items()}
        return sorted(avg.items(), key=lambda x: x[1], reverse=True)[:k]
