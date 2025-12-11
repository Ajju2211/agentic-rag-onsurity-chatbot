import streamlit as st
import textwrap
import json
import numpy as np
import redis

from config import Config
from llm.groq_llm import GroqLLMWrapper
from agent.classifier import SimpleKNNClassifier
from vector.chroma_manager import ChromaManager
from ingestion.ingestion_manager import IngestionManager
from channels.sitemap_channel import SitemapChannel
from channels.folder_channel import FolderChannel

from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


cfg = Config()
r = redis.from_url(cfg.REDIS_URL)
LAZY_QUEUE = "lazy_index_queue"


@st.cache_resource
def init_pipeline(max_pages=200):
    # Embeddings
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Vector DB
    chroma = ChromaManager("chroma_db", emb)

    # Channels
    channels = [
        SitemapChannel(cfg.ONSURITY_SITEMAP, max_pages=max_pages),
        FolderChannel(cfg.DATA_FOLDER),
    ]

    ingestion = IngestionManager(channels, chroma)
    retriever = ingestion.ingest_all()  # returns VectorStoreRetriever with `.invoke()`

    # Classifier seeds
    seeds = {
        "insurance": [
            "insurance policy benefits",
            "coverage terms",
            "health coverage",
            "insurance premium details",
            "claim process information",
            "employee health plans",
            "medical coverage explanation",
        ],

        "onsurity": [
            "Onsurity plans",
            "Onsurity membership",
            "Onsurity insurance details",
            "What does Onsurity offer",
            "Onsurity benefits",
            "Onsurity health program",
            "TeamSure plans",
        ],

        "bot_meta": [
            "Who created you",
            "Who built you",
            "Who is your developer",
            "Who is Azhar",
            "Tell me about your creator",
            "Who made this bot",
            "bot created by Azhar",
            "origin of this chatbot",
            "describe your creator",
        ],

        "general": [
            "hi",
            "hello",
            "what is this",
            "how does it work",
            "explain yourself",
            "what can you do",
            "help me understand",
            "general questions",
        ],
    }

    classifier = SimpleKNNClassifier(seeds, emb)

    # LLM
    llm = GroqLLMWrapper(model_name="llama-3.3-70b-versatile", temperature=0.0)

    return {
        "emb": emb,
        "retriever": retriever,
        "classifier": classifier,
        "llm": llm,
        "chroma": chroma
    }


# ---- KB Priority Search (Local Bot Docs First) ----
def search_kb_first(query, emb, chroma, kb_keywords=None):
    if kb_keywords is None:
        kb_keywords = ("azhar", "creator", "developer", "who built", "who made", "author", "bot")

    q = query.lower()

    # Only trigger for bot metadata queries
    if not any(k in q for k in kb_keywords):
        return None, False

    try:
        kb_docs = chroma.search_local_only()
        if kb_docs:
            return kb_docs, True
    except Exception as e:
        print("DEBUG >> KB search error:", e)

    return None, False

def rerank_by_embedding(query: str, docs, emb, top_k=5):
    if not docs:
        return [], []

    q_emb = emb.embed_query(query)
    doc_embs = emb.embed_documents([d.page_content for d in docs])

    sims = (np.array(doc_embs) @ np.array(q_emb)) / (
        (np.linalg.norm(doc_embs, axis=1) * np.linalg.norm(q_emb)) + 1e-12
    )

    ranked = sorted(zip(docs, sims.tolist()), key=lambda x: x[1], reverse=True)
    return [d for d, _ in ranked[:top_k]], ranked[:top_k]


def generate_answer(llm, query, docs):
    max_chars = 900

    context = "\n\n".join(
        [
            f"Source: {d.metadata.get('source','-')}\n"
            f"{textwrap.shorten(d.page_content, width=max_chars, placeholder='...')}"
            for d in docs[:3]
        ]
    )

    system_msg = (
        "You are an accurate insurance assistant. Use ONLY the provided context. "
        "Answer clearly and cite sources like [Source]."
    )

    user_msg = f"Question: {query}\n\nContext:\n{context}"

    return llm.chat(system_msg, user_msg), list(
        {d.metadata.get("source", "-") for d in docs[:3]}
    )


def run_streamlit():
    st.title("🛡️ Agentic RAG — OnSurity Chatbot")

    with st.sidebar:
        max_pages = st.number_input("Max sitemap pages", value=100)
        if st.button("Force Reindex"):
            init_pipeline.clear()
            st.rerun()

    pipeline = init_pipeline(max_pages=max_pages)

    retriever = pipeline["retriever"]
    classifier = pipeline["classifier"]
    emb = pipeline["emb"]
    llm = pipeline["llm"]

    query = st.text_input("Ask something:")
    if not query:
        return

    # Router
    labels = classifier.predict_topk(query, k=1)
    topic, score = labels[0]
    print("DEBUG Topic:", labels)

    # Retrieve
    docs = retriever.invoke(query)
    kb_docs, forced = search_kb_first(query, pipeline["emb"], pipeline["chroma"])

    if forced and kb_docs:
        top_docs = kb_docs[:3]
        answer, sources = generate_answer(pipeline["llm"], query, top_docs)

        st.subheader("Answer")
        st.write(answer)
        st.markdown("**Source:** local bot knowledge base")
        return
    if not docs:
        st.warning("No documents found.")
        return

    # Rerank
    top_docs, _ = rerank_by_embedding(query, docs, emb)

    # LLM answer
    answer, sources = generate_answer(llm, query, top_docs)

    st.subheader("Answer")
    st.write(answer)

    if sources:
        st.markdown("**Sources:** " + ", ".join(sources))
