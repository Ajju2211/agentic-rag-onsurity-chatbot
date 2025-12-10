from embeddings.local_embeddings import LocalEmbeddings
import numpy as np

class SimpleKNNClassifier:
    def __init__(self, labels_examples: dict, emb_model: LocalEmbeddings):
        self.labels = list(labels_examples.keys())
        self.examples = [v for k in self.labels for v in labels_examples[k]]
        self.example_labels = [k for k in self.labels for _ in labels_examples[k]]
        self.emb = emb_model
        self.example_embs = self.emb.model.encode(self.examples, convert_to_numpy=True)

    def predict_topk(self, text: str, k: int = 2):
        q = self.emb.model.encode([text], convert_to_numpy=True)[0]
        sims = (self.example_embs @ q) / (np.linalg.norm(self.example_embs, axis=1) * (np.linalg.norm(q) + 1e-12))
        label_scores = {}
        for lbl, sim in zip(self.example_labels, sims):
            label_scores.setdefault(lbl, []).append(sim)
        avg_scores = {lbl: float(sum(v)/len(v)) for lbl,v in label_scores.items()}
        sorted_labels = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_labels[:k]
