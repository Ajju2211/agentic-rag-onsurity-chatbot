import glob
import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.schema import Document
from .base import BaseChannel
import logging

logger = logging.getLogger(__name__)

class FolderChannel(BaseChannel):
    def __init__(self, folder_path: str):
        self.folder_path = folder_path

    def name(self):
        return 'folder_channel'

    def load_documents(self) -> List[Document]:
        all_docs = []
        # Load text files
        for txt in glob.glob(os.path.join(self.folder_path, '*.txt')):
            try:
                loader = TextLoader(txt, encoding='utf-8')
                parts = loader.load()
                for p in parts:
                    if 'source' not in p.metadata:
                        p.metadata['source'] = os.path.basename(txt)
                    all_docs.append(p)
            except Exception as e:
                logger.warning('Failed to load txt %s: %s', txt, e)

        # Load PDFs page-wise
        for pdf in glob.glob(os.path.join(self.folder_path, '*.pdf')):
            try:
                loader = PyPDFLoader(pdf)
                pages = loader.load()
                for i, p in enumerate(pages):
                    if 'source' not in p.metadata:
                        p.metadata['source'] = os.path.basename(pdf)
                    p.metadata['page'] = i + 1
                all_docs.extend(pages)
            except Exception as e:
                logger.warning('Failed to load pdf %s: %s', pdf, e)

        return all_docs
