import asyncio, aiohttp, requests, logging
from bs4 import BeautifulSoup
from typing import List
from langchain_core.documents import Document
from .base import BaseChannel

logger = logging.getLogger(__name__)

class SitemapChannel(BaseChannel):
    def __init__(self, url: str, max_pages: int = 200):
        self.url = url
        self.max_pages = max_pages

    def name(self): return "sitemap_channel"

    async def _fetch(self, session, url):
        try:
            async with session.get(url, timeout=20) as resp:
                return await resp.text()
        except:
            return None

    def _parse_xml(self, xml_text: str) -> List[str]:
        soup = BeautifulSoup(xml_text, "xml")
        return [loc.text for loc in soup.find_all("loc")]

    async def _gather_pages(self, urls):
        docs = []
        async with aiohttp.ClientSession() as session:
            results = await asyncio.gather(*[self._fetch(session, u) for u in urls])
            for url, html in zip(urls, results):
                if not html: continue
                soup = BeautifulSoup(html, "html.parser")
                for s in soup(["script","style"]): s.decompose()
                txt = soup.get_text("
", strip=True)
                docs.append(Document(page_content=txt, metadata={"source": url}))
                if len(docs) >= self.max_pages: break
        return docs

    def load_documents(self):
        try:
            xml = requests.get(self.url, timeout=20).text
        except:
            return []
        urls = []
        for u in self._parse_xml(xml):
            if u.endswith(".xml"):
                try:
                    sub = requests.get(u, timeout=15).text
                    urls += self._parse_xml(sub)
                except:
                    pass
            else:
                urls.append(u)
        urls = urls[: self.max_pages]
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._gather_pages(urls))
