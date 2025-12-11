from langchain_chroma import Chroma


class ChromaManager:
    def __init__(self, persist_dir, embedding_model):
        self.embedding_model = embedding_model

        self.store = Chroma(
            collection_name="insurance_docs",
            persist_directory=persist_dir,
            embedding_function=embedding_model,
        )

    def add_documents(self, docs):
        if not docs:
            return
        texts = [d.page_content for d in docs]
        metas = [d.metadata for d in docs]
        self.store.add_texts(texts=texts, metadatas=metas)

    def search_local_only(self):
        """Return KB-only docs from data/insurance_docs folder."""
        try:
            results = self.store.similarity_search("bot info", k=10)
            filtered = [
                d for d in results
                if "insurance_docs" in d.metadata.get("source", "")
            ]
            return filtered
        except Exception as e:
            print("DEBUG >> search_local_only error:", e)
            return []

    def as_retriever(self):
        return self.store.as_retriever(
            search_kwargs={"k": 8}
        )  # retriever supports `.invoke()`
