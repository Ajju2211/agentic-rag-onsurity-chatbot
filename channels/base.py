from typing import List
from langchain_core.documents import Document

class BaseChannel:
    def load_documents(self) -> List[Document]:
        raise NotImplementedError()
    def name(self) -> str:
        raise NotImplementedError()
