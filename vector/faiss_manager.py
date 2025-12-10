import os
import json
import hashlib
from typing import List, Dict
from langchain_community.vectorstores import FAISS
from langchain.schema import Document
from langchain.embeddings.base import Embeddings

MANIFEST_NAME = 'manifest.json'

class FAISSManager:
    def __init__(self, index_dir: str, embeddings: Embeddings):
        self.index_dir = index_dir
        self.emb = embeddings
        self.manifest_path = os.path.join(self.index_dir, MANIFEST_NAME)
        os.makedirs(self.index_dir, exist_ok=True)

    def index_exists(self) -> bool:
        flag = os.path.join(self.index_dir, 'indexed.flag')
        return os.path.isdir(self.index_dir) and os.path.exists(flag)

    def save_index(self, vectordb: FAISS):
        vectordb.save_local(self.index_dir)
        with open(os.path.join(self.index_dir, 'indexed.flag'), 'w') as f:
            f.write('indexed')

    def load_index(self) -> FAISS:
        return FAISS.load_local(self.index_dir, self.emb)

    def build_index(self, docs: List[Document]) -> FAISS:
        return FAISS.from_documents(docs, self.emb)

    def upsert_documents(self, docs: List[Document], batch_size: int = 64):
        if not docs:
            return
        if self.index_exists():
            try:
                vectordb = self.load_index()
            except Exception:
                vectordb = None
        else:
            vectordb = None

        if vectordb is None:
            vectordb = self.build_index(docs)
            self.save_index(vectordb)
            self._update_manifest_with_docs(docs)
            return

        try:
            vectordb.add_documents(docs)
        except Exception:
            # fallback: rebuild (not ideal for huge indexes)
            vectordb = self.build_index(docs)

        self.save_index(vectordb)
        self._update_manifest_with_docs(docs)

    def _update_manifest_with_docs(self, docs: List[Document]):
        m = self._load_manifest()
        for d in docs:
            src = d.metadata.get('source') or d.metadata.get('url') or 'unknown'
            h = hashlib.sha256(d.page_content.encode('utf-8')).hexdigest()
            m[src] = {
                'hash': h,
                'last_indexed': int(os.path.getmtime(self.index_dir))
            }
        self._save_manifest(m)

    def _load_manifest(self) -> Dict:
        if not os.path.exists(self.manifest_path):
            return {}
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_manifest(self, manifest: Dict):
        with open(self.manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

    def get_manifest(self) -> Dict:
        return self._load_manifest()
