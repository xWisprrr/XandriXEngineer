import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import List, Optional
from urllib.parse import quote_plus

import httpx

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: List[str] = []
        self._skip_tags = {"script", "style", "noscript", "head"}
        self._current_skip = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in self._skip_tags:
            self._current_skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._current_skip > 0:
            self._current_skip -= 1

    def handle_data(self, data: str) -> None:
        if self._current_skip == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


class BrowserTool:
    name = "browser"

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }

    async def fetch_url(self, url: str) -> str:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    parser = _TextExtractor()
                    parser.feed(response.text)
                    return parser.get_text()
                return response.text
            except httpx.HTTPStatusError as exc:
                logger.error(f"HTTP error fetching {url}: {exc}")
                return f"Error: HTTP {exc.response.status_code}"
            except Exception as exc:
                logger.error(f"Error fetching {url}: {exc}")
                return f"Error: {exc}"

    async def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Perform a DuckDuckGo search and return results."""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        results: List[SearchResult] = []
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                response = await client.get(search_url, headers=self.headers)
                response.raise_for_status()
                html = response.text

                # Basic parsing of DuckDuckGo HTML results
                title_pattern = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
                snippet_pattern = re.compile(r'class="result__snippet"[^>]*>(.*?)</div>', re.DOTALL)

                titles_urls = title_pattern.findall(html)
                snippets_raw = snippet_pattern.findall(html)

                for i, (url, title_html) in enumerate(titles_urls[:num_results]):
                    title_clean = re.sub(r"<[^>]+>", "", title_html).strip()
                    snippet_clean = ""
                    if i < len(snippets_raw):
                        snippet_clean = re.sub(r"<[^>]+>", "", snippets_raw[i]).strip()
                    results.append(SearchResult(title=title_clean, url=url, snippet=snippet_clean))
            except Exception as exc:
                logger.error(f"Search error: {exc}")
        return results

    async def fetch_documentation(self, library: str, language: str = "python") -> str:
        doc_urls = {
            "python": f"https://docs.python.org/3/library/{library}.html",
            "javascript": f"https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/{library}",
            "node": f"https://nodejs.org/api/{library}.html",
        }
        url = doc_urls.get(language.lower(), f"https://docs.python.org/3/library/{library}.html")
        return await self.fetch_url(url)
