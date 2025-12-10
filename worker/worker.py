import os
import time
import json
import redis
import requests
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from langchain.schema import Document
from vector.faiss_manager import FAISSManager
from embeddings.local_embeddings import LocalEmbeddings
from channels.sitemap_channel import SitemapChannel
from channels.folder_channel import FolderChannel

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
r = redis.from_url(REDIS_URL)

INSURANCE_INDEX_DIR = os.getenv('INSURANCE_INDEX_DIR', 'indexes/insurance_faiss')
ONSURITY_INDEX_DIR = os.getenv('ONSURITY_INDEX_DIR', 'indexes/onsurity_faiss')
ONSURITY_SITEMAP = os.getenv('ONSURITY_SITEMAP', 'https://www.onsurity.com/sitemap_index.xml')
EMB_MODEL = os.getenv('EMB_MODEL', 'all-MiniLM-L6-v2')

LAZY_QUEUE = 'lazy_index_queue'
SCHEDULE_LAST_RUN = 'sitemap_last_run'

local_emb = LocalEmbeddings(model_name=EMB_MODEL)
from langchain.embeddings.base import Embeddings
class STEmbeddings(Embeddings):
    def __init__(self, model):
        self.model = model
    def embed_documents(self, texts):
        return self.model.embed_documents(texts)
    def embed_query(self, text):
        return self.model.embed_query(text)

st_emb = STEmbeddings(local_emb)

insurance_faiss = FAISSManager(index_dir=INSURANCE_INDEX_DIR, embeddings=st_emb)
onsurity_faiss = FAISSManager(index_dir=ONSURITY_INDEX_DIR, embeddings=st_emb)

def fetch_sitemap_index(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def parse_xml_for_locs(xml_text):
    soup = BeautifulSoup(xml_text, 'xml')
    locs = [loc.text for loc in soup.find_all('loc') if loc.text.startswith('http')]
    return locs

import hashlib

def compute_text_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def sitemap_change_detection_and_index():
    logger.info('Starting sitemap diff check')
    try:
        xml = fetch_sitemap_index(ONSURITY_SITEMAP)
    except Exception as e:
        logger.exception('Failed to fetch sitemap index: %s', e)
        return

    top_locs = parse_xml_for_locs(xml)
    page_urls = []
    for loc in top_locs:
        if loc.endswith('.xml'):
            try:
                inner = fetch_sitemap_index(loc)
                page_urls.extend(parse_xml_for_locs(inner))
            except Exception:
                continue
        else:
            page_urls.append(loc)

    page_urls = page_urls[:1000]

    manifest = onsurity_faiss.get_manifest()
    to_upsert = []

    for url in page_urls:
        try:
            rresp = requests.get(url, timeout=15)
            if rresp.status_code != 200:
                continue
            text = BeautifulSoup(rresp.text, 'html.parser')
            for s in text(['script','style','nav','header','footer','form','noscript']):
                s.decompose()
            body = text.get_text('\n', strip=True)
            h = compute_text_hash(body)
            old = manifest.get(url)
            if not old or old.get('hash') != h:
                logger.info('Detected change or new page: %s', url)
                to_upsert.append(Document(page_content=body, metadata={'source': url}))
        except Exception as e:
            logger.debug('Error fetching page %s: %s', url, e)
            continue

    if to_upsert:
        logger.info('Upserting %d changed pages into Onsurity FAISS', len(to_upsert))
        onsurity_faiss.upsert_documents(to_upsert)
    else:
        logger.info('No changes detected')

def process_lazy_job(job_payload: dict):
    t = job_payload.get('type')
    if t == 'onsurity_url':
        url = job_payload.get('url')
        try:
            rresp = requests.get(url, timeout=15)
            rresp.raise_for_status()
            soup = BeautifulSoup(rresp.text, 'html.parser')
            for s in soup(['script','style','nav','header','footer','form','noscript']):
                s.decompose()
            body = soup.get_text('\n', strip=True)
            doc = Document(page_content=body, metadata={'source': url})
            onsurity_faiss.upsert_documents([doc])
            logger.info('Lazy-indexed onsurity url: %s', url)
        except Exception as e:
            logger.exception('Lazy index failed for url %s: %s', url, e)
    elif t == 'insurance_text':
        text = job_payload.get('text')
        source = job_payload.get('source', 'lazy')
        doc = Document(page_content=text, metadata={'source': source})
        insurance_faiss.upsert_documents([doc])
        logger.info('Lazy-indexed insurance text source: %s', source)
    else:
        logger.warning('Unknown lazy job type: %s', t)

def main_loop():
    logger.info('Worker started')
    sitemap_change_detection_and_index()
    while True:
        try:
            job = r.lpop(LAZY_QUEUE)
            if job:
                try:
                    payload = json.loads(job)
                    process_lazy_job(payload)
                except Exception as e:
                    logger.exception('Failed to process lazy job: %s', e)
                    continue

            last_run = r.get(SCHEDULE_LAST_RUN)
            now = datetime.utcnow()
            do_run = False
            if not last_run:
                do_run = True
            else:
                last = datetime.fromisoformat(last_run.decode('utf-8'))
                if now - last > timedelta(hours=24):
                    do_run = True

            if do_run:
                logger.info('Running scheduled sitemap check')
                sitemap_change_detection_and_index()
                r.set(SCHEDULE_LAST_RUN, now.isoformat())

            time.sleep(2)

        except Exception as e:
            logger.exception('Worker loop error: %s', e)
            time.sleep(5)

if __name__ == '__main__':
    main_loop()
