"""
XandriX Engineer - Tool: Web Browser / Documentation Retrieval
"""
import re
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse

import httpx

from backend.core.logger import get_logger

logger = get_logger("tool.browser")


class WebBrowser:
    """Lightweight web browser for documentation retrieval and web search."""

    def __init__(self, timeout: int = 30):
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; XandriXEngineer/1.0; research bot)"
            },
        )

    async def fetch(self, url: str) -> str:
        """Fetch a URL and return cleaned text content."""
        logger.tool("browser", f"Fetching {url}")
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type:
                return self._html_to_text(resp.text)
            return resp.text
        except Exception as e:
            logger.tool("browser", f"Fetch failed: {e}")
            return f"Error fetching {url}: {e}"

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to readable plain text."""
        # Remove script and style blocks
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML comments
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        # Replace common block tags with newlines
        html = re.sub(r"<(br|hr|p|div|h[1-6]|li|tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
        # Remove remaining tags
        html = re.sub(r"<[^>]+>", "", html)
        # Decode HTML entities
        replacements = {
            "&amp;": "&", "&lt;": "<", "&gt;": ">",
            "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
        }
        for ent, char in replacements.items():
            html = html.replace(ent, char)
        # Normalize whitespace
        lines = [line.strip() for line in html.splitlines()]
        return "\n".join(line for line in lines if line)[:10000]  # limit length

    async def search_duckduckgo(self, query: str, max_results: int = 5) -> list[dict]:
        """Search DuckDuckGo and return results."""
        logger.tool("browser", f"Searching: {query}")
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            content = await self.fetch(url)

            # Parse results from text
            results = []
            lines = content.split("\n")
            current_result: dict = {}
            for line in lines:
                line = line.strip()
                if line.startswith("http") and not current_result.get("url"):
                    current_result["url"] = line
                elif current_result.get("url") and not current_result.get("title"):
                    current_result["title"] = line
                elif current_result.get("title") and line:
                    current_result["snippet"] = line
                    results.append(current_result)
                    current_result = {}
                    if len(results) >= max_results:
                        break

            return results
        except Exception as e:
            logger.tool("browser", f"Search failed: {e}")
            return []

    async def fetch_docs(self, technology: str, topic: str = "") -> str:
        """Fetch documentation for a specific technology."""
        doc_urls = {
            "python": f"https://docs.python.org/3/search.html?q={quote_plus(topic)}",
            "numpy": f"https://numpy.org/doc/stable/search.html?q={quote_plus(topic)}",
            "react": f"https://react.dev/search?q={quote_plus(topic)}",
            "fastapi": f"https://fastapi.tiangolo.com/search/?query={quote_plus(topic)}",
            "docker": f"https://docs.docker.com/search/?q={quote_plus(topic)}",
        }

        tech_lower = technology.lower()
        if tech_lower in doc_urls:
            return await self.fetch(doc_urls[tech_lower])

        # Fall back to web search
        results = await self.search_duckduckgo(f"{technology} {topic} documentation")
        if results:
            return await self.fetch(results[0]["url"])
        return f"No documentation found for {technology} {topic}"

    async def close(self) -> None:
        await self._client.aclose()
