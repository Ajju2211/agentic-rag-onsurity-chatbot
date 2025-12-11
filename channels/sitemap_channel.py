import asyncio
import concurrent.futures
import random
import time
from typing import List, Optional, Set, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.documents import Document

try:
    import brotlicffi as brotli
except Exception:
    brotli = None

try:
    import tls_client 
except Exception:
    tls_client = None

try:
    from playwright.sync_api import sync_playwright  # pip install playwright && playwright install
except Exception:
    sync_playwright = None


# ----------------------------
# ROTATING REAL BROWSER USER AGENTS
# ----------------------------
ROTATING_UAS = [
    # Chrome (Windows)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36",
    # Chrome (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36",
    # Safari (macOS)
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Mobile Chrome (Android)
    "Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/121.0.0.0 Mobile Safari/537.36",
    # Mobile Safari (iPhone)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/16.4 Mobile/15E148 Safari/604.1",
]

# ----------------------------
# Helper: build headers for human-like browsing
# ----------------------------
def build_headers(user_agent: str, referer: Optional[str] = None) -> dict:
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # We intentionally *do not* forcibly set Accept-Encoding; let client/server negotiate.
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }
    if referer:
        headers["Referer"] = referer
    return headers


# ----------------------------
# Safe decode helper
# ----------------------------
def _safe_decode(raw: bytes, encoding: Optional[str]) -> Optional[str]:
    enc = (encoding or "").lower()
    try:
        if enc == "br":
            if brotli:
                try:
                    return brotli.decompress(raw).decode("utf-8", errors="ignore")
                except Exception:
                    return raw.decode("utf-8", errors="ignore")
            # if no brotli lib, fall back to utf-8 ignoring errors
            return raw.decode("utf-8", errors="ignore")
        if enc == "gzip":
            import gzip
            return gzip.decompress(raw).decode("utf-8", errors="ignore")
        if enc == "deflate":
            import zlib
            try:
                return zlib.decompress(raw).decode("utf-8", errors="ignore")
            except Exception:
                # sometimes raw deflate needs raw mode
                return zlib.decompress(raw, -zlib.MAX_WBITS).decode("utf-8", errors="ignore")
        # no encoding header
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        try:
            return raw.decode("utf-8", errors="ignore")
        except Exception:
            return None


def _playwright_fetch(url: str, user_agent: str, timeout_sec: int = 30) -> Optional[str]:
    if sync_playwright is None:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(user_agent=user_agent)
            page = context.new_page()
            page.goto(url, timeout=timeout_sec * 1000)
            html = page.content()
            page.close()
            context.close()
            browser.close()
            return html
    except Exception as e:
        print(f"DEBUG >> Playwright fetch failed for {url}: {e}")
        return None


def _tls_client_fetch(url: str, headers: dict, fingerprint_id: Optional[str] = None) -> Optional[Tuple[str, int]]:
    if tls_client is None:
        return None
    try:
        try:
            sess = tls_client.Session(client_identifier=fingerprint_id) if fingerprint_id else tls_client.Session()
        except TypeError:
            sess = tls_client.Session()  # fallback
        resp = sess.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        text = _safe_decode(resp.content, resp.headers.get("Content-Encoding"))
        return text, resp.status_code
    except Exception as e:
        print(f"DEBUG >> tls-client fetch error for {url}: {e}")
        return None


# ----------------------------
# SitemapChannel Class (Option C)
# ----------------------------
class SitemapChannel:
    def __init__(
        self,
        sitemap_url: str,
        max_pages: int = 400,
        concurrency: int = 12,
        preferred_user_agent: Optional[str] = None,
        ua_pool: Optional[List[str]] = None,
        enable_playwright_fallback: bool = True,
        enable_tlsclient_fallback: bool = True,
    ):
        """
        sitemap_url: root sitemap (could be sitemap_index.xml)
        max_pages: max pages to fetch
        concurrency: parallel fetch concurrency
        preferred_user_agent: your real browser UA (preferred)
        ua_pool: optional list to rotate if preferred fails
        """
        self.sitemap_url = sitemap_url
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.preferred_user_agent = preferred_user_agent or ROTATING_UAS[0]
        self.ua_pool = ua_pool or ROTATING_UAS
        self.enable_playwright_fallback = enable_playwright_fallback
        self.enable_tlsclient_fallback = enable_tlsclient_fallback

        # memoization
        self._visited_sitemaps: Set[str] = set()
        self._visited_pages: Set[str] = set()

    # ----------------------------
    # Determine if text looks like sitemap xml
    # ----------------------------
    @staticmethod
    def _looks_like_sitemap(text: str) -> bool:
        t = (text or "").lower()
        return "<sitemapindex" in t or "<urlset" in t

    # ----------------------------
    # Parse sitemap xml and return nested sitemaps and page urls
    # ----------------------------
    @staticmethod
    def _parse_sitemap(xml: str) -> Tuple[List[str], List[str]]:
        soup = BeautifulSoup(xml, "lxml-xml")
        nested = []
        pages = []

        # nested sitemaps
        for s in soup.find_all("sitemap"):
            loc = s.find("loc")
            if loc and loc.text:
                nested.append(loc.text.strip())

        # url entries
        for u in soup.find_all("url"):
            loc = u.find("loc")
            if loc and loc.text:
                pages.append(loc.text.strip())

        # If sitemap is simple <loc> only (some sitemaps), also include those
        if not nested and not pages:
            for loc in soup.find_all("loc"):
                if loc and loc.text:
                    # heuristically separate xml vs pages by .xml suffix
                    url = loc.text.strip()
                    if url.endswith(".xml"):
                        nested.append(url)
                    else:
                        pages.append(url)

        return nested, pages

    async def _fetch_async(self, session: aiohttp.ClientSession, url: str, user_agent: str) -> Optional[str]:
        hdrs = build_headers(user_agent, referer=None)
        try:
            async with session.get(url, headers=hdrs, timeout=20) as resp:
                if resp.status in (403, 429):
                    return None
                try:
                    text = await resp.text()
                    if text:
                        return text
                except (UnicodeDecodeError, aiohttp.ClientPayloadError):
                    raw = await resp.read()
                    return _safe_decode(raw, resp.headers.get("Content-Encoding"))
        except Exception as e:
            # print(f"DEBUG >> aiohttp fetch error {url}: {e}")
            return None

    async def _robust_fetch(self, url: str) -> Optional[str]:
        # 1. try aiohttp with preferred UA
        async with aiohttp.ClientSession() as session:
            text = await self._fetch_async(session, url, self.preferred_user_agent)
            if text:
                return text

            # 2. rotate through pool (non-blocking minimal attempts)
            for _ in range(min(len(self.ua_pool), 4)):
                ua = random.choice(self.ua_pool)
                text = await self._fetch_async(session, url, ua)
                if text:
                    return text

        # 3. tls-client fallback (sync) if enabled
        if self.enable_tlsclient_fallback and tls_client is not None:
            for _ in range(2):
                ua = random.choice(self.ua_pool)
                headers = build_headers(ua)
                res = _tls_client_fetch(url, headers, fingerprint_id=None)
                if res:
                    text, status = res
                    if text:
                        return text

        # 4. Playwright fallback (slow but reliable)
        if self.enable_playwright_fallback and sync_playwright is not None:
            for ua in (self.preferred_user_agent, ) + tuple(self.ua_pool):
                html = _playwright_fetch(url, ua)
                if html:
                    return html

        return None

    async def crawl_sitemaps(self) -> List[str]:
        to_visit = [self.sitemap_url]
        found_pages: List[str] = []

        while to_visit and len(found_pages) < self.max_pages:
            sitemap = to_visit.pop()
            if sitemap in self._visited_sitemaps:
                continue
            self._visited_sitemaps.add(sitemap)

            xml = await self._robust_fetch(sitemap)
            if not xml:
                # print(f"DEBUG >> Could not fetch sitemap: {sitemap}")
                continue

            if not self._looks_like_sitemap(xml):
                soup = BeautifulSoup(xml, "html.parser")
                locs = [a.get("href") for a in soup.find_all("a", href=True)]
                for l in locs:
                    if not l:
                        continue
                    absolute = urljoin(sitemap, l)
                    if absolute.endswith(".xml"):
                        to_visit.append(absolute)
                    else:
                        if absolute not in self._visited_pages and len(found_pages) < self.max_pages:
                            self._visited_pages.add(absolute)
                            found_pages.append(absolute)
                continue

            nested, pages = self._parse_sitemap(xml)
            for ns in nested:
                if ns not in self._visited_sitemaps:
                    to_visit.append(ns)

            for p in pages:
                if len(found_pages) >= self.max_pages:
                    break
                if p not in self._visited_pages:
                    self._visited_pages.add(p)
                    found_pages.append(p)

        return found_pages

    async def _scrape_pages(self, urls: List[str]) -> List[Document]:
        docs: List[Document] = []
        sem = asyncio.Semaphore(self.concurrency)
        loop = asyncio.get_event_loop()

        async def worker(u: str):
            async with sem:
                text = await self._robust_fetch(u)
                if not text:
                    return None
                if text.strip().startswith("<?xml") or "<urlset" in text.lower() or "<sitemapindex" in text.lower():
                    soup = BeautifulSoup(text, "lxml-xml")
                else:
                    soup = BeautifulSoup(text, "html.parser")
                for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                    tag.decompose()
                page_text = soup.get_text(separator="\n", strip=True)
                if not page_text:
                    return None
                return Document(page_content=page_text[:20000], metadata={"source": u})

        tasks = [worker(u) for u in urls]
        results = await asyncio.gather(*tasks)
        for r in results:
            if r:
                docs.append(r)
        return docs

    def load_documents(self) -> List[Document]:
        start = time.time()
        pages = asyncio.run(self.crawl_sitemaps())
        if not pages:
            print("DEBUG >> No pages found in sitemap")
            return []

        docs = asyncio.run(self._scrape_pages(pages[: self.max_pages]))
        print(f"DEBUG >> SitemapChannel: found {len(pages)} pages, scraped {len(docs)} docs in {time.time()-start:.2f}s")
        return docs
