import streamlit as st
from config import Config
from embeddings.local_embeddings import LocalEmbeddings
from channels.folder_channel import FolderChannel
from channels.sitemap_channel import SitemapChannel
from ingestion.ingestion_manager import IngestionManager
from vector.chroma_manager import ChromaManager
from agent.classifier import SimpleKNNClassifier
from agent.agent_builder import AgentBuilder

cfg = Config()

@st.cache_resource
def pipeline(max_pages=20):
    emb = LocalEmbeddings(cfg.EMBEDDING_MODEL)
    chroma = ChromaManager(cfg.CHROMA_DB_DIR, cfg.EMBEDDING_MODEL)
    folder = FolderChannel(cfg.DATA_FOLDER)
    ing = IngestionManager([folder], chroma)
    retr = ing.ingest_all()

    seeds = {
        "insurance": ["policy coverage", "claim process", "waiting period"],
        "onsurity": ["onsurity pricing", "heightened health benefits"],
        "wiki": ["what is", "who is"]
    }
    clf = SimpleKNNClassifier(seeds, emb)
    llm = AgentBuilder(cfg.OPENAI_API_KEY).build()
    return retr, clf, llm

def run_streamlit():
    st.title("Agentic RAG Chatbot - 2025")

    q = st.text_input("Ask:")
    retr, clf, llm = pipeline()

    if q:
        label, score = clf.predict(q,1)[0]
        ctx_docs = retr(q)
        ctx = "
---
".join(d.page_content[:800] for d in ctx_docs)

        prompt = f"You are an assistant. Use context.
Context:
{ctx}
Question: {q}"
        if llm:
            ans = llm.invoke(prompt).content
        else:
            ans = ctx_docs[0].page_content[:500] if ctx_docs else "No context."
        st.write(ans)
