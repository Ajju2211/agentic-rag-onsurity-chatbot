import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DATA_FOLDER = os.getenv('DATA_FOLDER', 'data/insurance_docs')
    INSURANCE_INDEX = os.getenv('INSURANCE_INDEX', 'indexes/insurance_faiss')
    ONSURITY_INDEX = os.getenv('ONSURITY_INDEX', 'indexes/onsurity_faiss')
    ONSURITY_SITEMAP = os.getenv('ONSURITY_SITEMAP', 'https://www.onsurity.com/sitemap_index.xml')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    MAX_SITEMAP_PAGES = int(os.getenv('MAX_SITEMAP_PAGES', '500'))
