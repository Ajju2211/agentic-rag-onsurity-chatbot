from typing import List
from langchain.schema import Document

class BaseChannel:
    def load_documents(self) -> List[Document]:
        raise NotImplementedError()

    def name(self) -> str:
        raise NotImplementedError()
