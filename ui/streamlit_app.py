import streamlit as st
from config import Config
from embeddings.local_embeddings import LocalEmbeddings
from vector.faiss_manager import FAISSManager
from channels.folder_channel import FolderChannel
from channels.sitemap_channel import SitemapChannel
from ingestion.ingestion_manager import IngestionManager
from agent.classifier import SimpleKNNClassifier
from agent.agent_builder import AgentBuilder
from langchain.chat_models import ChatOpenAI
from langchain.tools.base import Tool
from langchain_community.utilities import WikipediaAPIWrapper, ArxivAPIWrapper
from langchain_community.tools import WikipediaQueryRun
from langchain import hub
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
import os, time, json
import redis

cfg = Config()
REDIS_URL = cfg.REDIS_URL
r = redis.from_url(REDIS_URL)
LAZY_QUEUE = 'lazy_index_queue'

from langchain.embeddings.base import Embeddings
class STEmbeddings(Embeddings):
    def __init__(self, model):
        self.model = model
    def embed_documents(self, texts):
        return self.model.embed_documents(texts)
    def embed_query(self, text):
        return self.model.embed_query(text)

@st.cache_resource
def init_pipeline(reindex: bool, max_pages: int):
    emb = LocalEmbeddings(model_name=cfg.EMBEDDING_MODEL)
    st_emb = STEmbeddings(emb)

    insurance_faiss = FAISSManager(index_dir=cfg.INSURANCE_INDEX, embeddings=st_emb)
    onsurity_faiss = FAISSManager(index_dir=cfg.ONSURITY_INDEX, embeddings=st_emb)

    folder_ch = FolderChannel(cfg.DATA_FOLDER)
    sitemap_ch = SitemapChannel(cfg.ONSURITY_SITEMAP, max_pages=max_pages)

    insurance_ing = IngestionManager([folder_ch], insurance_faiss)
    onsurity_ing = IngestionManager([sitemap_ch], onsurity_faiss)

    insurance_retriever = insurance_ing.ingest_all(persist=True)
    onsurity_retriever = onsurity_ing.ingest_all(persist=True)

    seeds = {
        'insurance': ['what does my policy cover', 'claim waiting period', 'exclusions in my policy'],
        'onsurity': ['onsurity benefits', 'onsurity pricing', 'onsurity partners'],
        'wiki': ['who is', 'what is', 'when did'],
        'arxiv': ['paper', 'arxiv', 'research']
    }
    classifier = SimpleKNNClassifier(labels_examples=seeds, emb_model=emb)

    llm = None
    if cfg.OPENAI_API_KEY:
        llm = ChatOpenAI(api_key=cfg.OPENAI_API_KEY, model='gpt-4o-mini', temperature=0.0)

    wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    arxiv_tool = Tool(name='arxiv_search', func=lambda q: ArxivAPIWrapper().run(q), description='ArXiv search')
    tools = [wiki_tool, arxiv_tool]
    agent_executor = None
    if llm:
        agent_executor = AgentBuilder(llm=llm, tools=tools).build()

    return {
        'emb': emb,
        'insurance_retriever': insurance_retriever,
        'onsurity_retriever': onsurity_retriever,
        'classifier': classifier,
        'agent_executor': agent_executor,
        'llm': llm
    }

FINAL_PROMPT = """            You are an insurance assistant. Use the provided context to answer the question clearly and simply.
Do NOT output any JSON or special sections. Keep sentences short and friendly.

CONTEXT:
{context}

QUESTION:
{question}
"""

def run_streamlit():
    st.set_page_config(page_title='Agentic RAG Insurance', layout='wide')
    st.title('Agentic RAG — Insurance Chatbot (Clean Answers)')

    with st.sidebar:
        st.header('Settings')
        max_pages = st.number_input('Max pages to crawl (onsurity)', value=200, step=50)
        reindex = st.button('Force Reindex')
        st.write('Local docs folder:')
        st.write(cfg.DATA_FOLDER)
        st.write('Onsurity sitemap:')
        st.write(cfg.ONSURITY_SITEMAP)

    pipeline = init_pipeline(reindex=reindex, max_pages=max_pages)

    st.sidebar.markdown('**Sources**')
    st.sidebar.write('- Local insurance folder')
    st.sidebar.write('- Onsurity sitemap (async crawler)')

    query = st.text_input('Ask your question:')

    if query:
        with st.spinner('Routing & retrieving...'):
            classifier = pipeline['classifier']
            top_labels = classifier.predict_topk(query, k=2)
            preferred = top_labels[0][0]
            pref_score = top_labels[0][1]
            score_threshold = 0.45

            if preferred in ('insurance', 'onsurity') and pref_score >= score_threshold:
                retriever = pipeline['insurance_retriever'] if preferred == 'insurance' else pipeline['onsurity_retriever']
                docs = retriever.get_relevant_documents(query)[:6]
                context = '\n\n'.join([f"Source: {d.metadata.get('source','-')}\n{d.page_content[:1200]}" for d in docs])
                prompt = FINAL_PROMPT.format(context=context, question=query)

                if pipeline['llm']:
                    resp = pipeline['llm'].generate([{'role':'user','content':prompt}])
                    try:
                        out = resp.generations[0][0].text
                    except Exception:
                        out = str(resp)
                else:
                    out = 'I found these relevant excerpts:\n\n' + '\n---\n'.join([d.page_content[:800] for d in docs])

                st.subheader('Answer')
                st.write(out)

                if not docs or len(docs) == 0 or (len(docs) > 0 and len(docs[0].page_content) < 100):
                    try:
                        r.rpush(LAZY_QUEUE, json.dumps({'type': 'sitemap_refresh'}))
                    except Exception:
                        pass

            else:
                agent = pipeline['agent_executor']
                if agent:
                    res = agent.invoke({'input': query})
                    if hasattr(res, 'output'):
                        out = res.output
                    else:
                        out = str(res)
                    st.subheader('Answer')
                    st.write(out)
                else:
                    docs_i = pipeline['insurance_retriever'].get_relevant_documents(query)[:4]
                    docs_o = pipeline['onsurity_retriever'].get_relevant_documents(query)[:4]
                    out = 'I found these relevant excerpts:\n\n' + '\n---\n'.join([d.page_content[:800] for d in (docs_i+docs_o)])
                    st.subheader('Answer (retrieved context)')
                    st.write(out)
