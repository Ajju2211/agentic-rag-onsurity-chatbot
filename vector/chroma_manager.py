import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document

class ChromaManager:
    def __init__(self, persist_directory='chroma_db', embedding_model='all-MiniLM-L6-v2'):
        os.makedirs(persist_directory, exist_ok=True)
        self.client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_directory))
        self.embedding_model = SentenceTransformer(embedding_model)
        try:
            self.collection = self.client.get_collection("docs")
        except:
            self.collection = self.client.create_collection("docs")

    def has_index(self):
        try:
            return self.collection.count() > 0
        except:
            return False

    def add_documents(self, docs):
        texts = [d.page_content for d in docs]
        metas = [d.metadata for d in docs]
        ids = [f"id_{i}" for i in range(len(docs))]
        embs = self.embedding_model.encode(texts, convert_to_numpy=True).tolist()
        self.collection.add(ids=ids, documents=texts, metadatas=metas, embeddings=embs)

    def persist(self):
        self.client.persist()

    def get_retriever(self, k=5):
        def fn(query):
            q = self.embedding_model.encode([query], convert_to_numpy=True)[0].tolist()
            res = self.collection.query(query_embeddings=[q], n_results=k, include=["documents","metadatas"])
            docs = []
            for t, m in zip(res["documents"][0], res["metadatas"][0]):
                docs.append(Document(page_content=t, metadata=m))
            return docs
        return fn
