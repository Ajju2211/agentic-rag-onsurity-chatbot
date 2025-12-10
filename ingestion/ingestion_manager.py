from typing import List
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from vector.faiss_manager import FAISSManager
import logging

logger = logging.getLogger(__name__)

class IngestionManager:
    def __init__(self, channels: List, vector_manager: FAISSManager, chunk_size: int = 800, chunk_overlap: int = 150):
        self.channels = channels
        self.vector_manager = vector_manager
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_all(self, persist: bool = True):
        if self.vector_manager.index_exists():
            try:
                return self.vector_manager.load_index().as_retriever()
            except Exception:
                logger.warning('Failed loading existing index, will rebuild')

        all_docs = []
        for ch in self.channels:
            try:
                docs = ch.load_documents()
                logger.info('Channel %s returned %d docs', ch.name(), len(docs))
                all_docs.extend(docs)
            except Exception as e:
                logger.warning('Channel %s failed: %s', ch.name(), e)

        if not all_docs:
            raise ValueError('No documents to index')

        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
        split_docs = splitter.split_documents(all_docs)

        vectordb = self.vector_manager.build_index(split_docs)
        if persist:
            self.vector_manager.save_index(vectordb)
        return vectordb.as_retriever()
