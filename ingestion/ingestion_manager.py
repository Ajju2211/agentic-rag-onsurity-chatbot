from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector.chroma_manager import ChromaManager
import logging

logger = logging.getLogger(__name__)

class IngestionManager:
    def __init__(self, channels, chroma: ChromaManager, chunk_size=800, chunk_overlap=150):
        self.channels = channels
        self.chroma = chroma
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_all(self, persist=True):
        if self.chroma.has_index():
            return self.chroma.get_retriever()

        docs = []
        for ch in self.channels:
            try:
                ds = ch.load_documents()
                docs.extend(ds)
            except Exception as e:
                logger.warning("Channel error: %s", e)

        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        chunks = splitter.split_documents(docs)
        self.chroma.add_documents(chunks)
        if persist: self.chroma.persist()
        return self.chroma.get_retriever()
