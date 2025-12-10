import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List
from langchain.schema import Document
from .base import BaseChannel
import requests
import logging

logger = logging.getLogger(__name__)

class SitemapChannel(BaseChannel):
    def __init__(self, sitemap_index_url: str, max_pages: int = 500):
        self.sitemap_index_url = sitemap_index_url
        self.max_pages = max_pages

    def name(self):
        return 'sitemap_channel'

    async def _fetch(self, session, url):
        try:
            async with session.get(url, timeout=15) as resp:
                return await resp.text()
        except Exception as e:
            logger.debug('fetch failed %s: %s', url, e)
            return None

    async def _gather_pages(self, urls: List[str]) -> List[Document]:
        docs = []
        headers = {'User-Agent': 'AgenticRAG/1.0'}
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self._fetch(session, u) for u in urls]
            results = await asyncio.gather(*tasks)
            for url, html in zip(urls, results):
                if not html:
                    continue
                soup = BeautifulSoup(html, 'html.parser')
                for s in soup(['script','style','nav','header','footer','form','noscript']):
                    s.decompose()
                text = soup.get_text('\n', strip=True)
                if text:
                    docs.append(Document(page_content=text, metadata={'source': url}))
                if len(docs) >= self.max_pages:
                    break
        return docs

    def _parse_xml(self, xml_text: str) -> List[str]:
        soup = BeautifulSoup(xml_text, 'xml')
        urls = [loc.text for loc in soup.find_all('loc') if loc.text.startswith('http')]
        return urls

    def load_documents(self) -> List[Document]:
        try:
            resp = requests.get(self.sitemap_index_url, timeout=15)
            resp.raise_for_status()
            xml = resp.text
        except Exception as e:
            logger.warning('Failed to fetch sitemap index: %s', e)
            return []

        urls = self._parse_xml(xml)
        page_urls = []
        for u in urls:
            if u.endswith('.xml'):
                try:
                    r = requests.get(u, timeout=15)
                    r.raise_for_status()
                    page_urls.extend(self._parse_xml(r.text))
                except Exception:
                    continue
            else:
                page_urls.append(u)
            if len(page_urls) >= self.max_pages:
                break

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        docs = loop.run_until_complete(self._gather_pages(page_urls[:self.max_pages]))
        return docs
