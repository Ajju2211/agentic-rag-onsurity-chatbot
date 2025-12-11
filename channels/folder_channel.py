import glob, os, logging
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from .base import BaseChannel

logger = logging.getLogger(__name__)

class FolderChannel(BaseChannel):
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
    def name(self): return "folder_channel"

    def load_documents(self) -> List[Document]:
        docs = []
        for txt in glob.glob(os.path.join(self.folder_path, "*.txt")):
            try:
                parts = TextLoader(txt).load()
                for p in parts:
                    md = p.metadata or {}
                    md.setdefault("source", os.path.basename(txt))
                    docs.append(Document(page_content=p.page_content, metadata=md))
            except Exception as e:
                logger.warning("TXT fail: %s", e)

        for pdf in glob.glob(os.path.join(self.folder_path, "*.pdf")):
            try:
                pages = PyPDFLoader(pdf).load()
                for i, p in enumerate(pages):
                    md = p.metadata or {}
                    md.setdefault("source", os.path.basename(pdf))
                    md["page"] = i + 1
                    docs.append(Document(page_content=p.page_content, metadata=md))
            except Exception as e:
                logger.warning("PDF fail: %s", e)

        return docs
