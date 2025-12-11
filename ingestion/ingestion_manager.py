class IngestionManager:
    def __init__(self, channels, chroma):
        self.channels = channels
        self.chroma = chroma

    def ingest_all(self):
        all_docs = []

        for ch in self.channels:
            docs = ch.load_documents()
            if docs:
                all_docs.extend(docs)

        self.chroma.add_documents(all_docs)
        return self.chroma.as_retriever()
