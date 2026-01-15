import re
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class WebContent:
    """Result of web content extraction."""
    text: str
    title: Optional[str] = None
    url: str = ""
    site_name: Optional[str] = None
    published_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class WebProcessor:
    """Processor for web content extraction."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SecondBrain/1.0; +https://secondbrain.app)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    async def fetch_and_extract(self, url: str) -> WebContent:
        """
        Fetch a URL and extract its main content.

        Args:
            url: The URL to fetch

        Returns:
            WebContent with extracted text and metadata
        """
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            html = response.text

        return self._extract_content(html, url)

    def _extract_content(self, html: str, url: str) -> WebContent:
        """Extract main content from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for element in soup.find_all([
            "script", "style", "nav", "footer", "header",
            "aside", "form", "iframe", "noscript"
        ]):
            element.decompose()

        # Remove elements by common ad/nav classes
        for element in soup.find_all(class_=re.compile(
            r"(nav|menu|sidebar|footer|header|ad|advertisement|social|share|comment)",
            re.I
        )):
            element.decompose()

        # Get title
        title = None
        if soup.title:
            title = soup.title.string
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content")
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Get site name
        site_name = None
        og_site = soup.find("meta", property="og:site_name")
        if og_site:
            site_name = og_site.get("content")
        if not site_name:
            parsed = urlparse(url)
            site_name = parsed.netloc

        # Get published date
        published_at = None
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            try:
                published_at = datetime.fromisoformat(
                    date_meta.get("content", "").replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Try to find main content
        main_content = None
        for selector in ["article", "main", '[role="main"]', ".content", "#content"]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup.body or soup

        # Extract text
        text = self._clean_text(main_content.get_text(separator="\n"))

        metadata = {
            "url": url,
            "fetched_at": datetime.utcnow().isoformat(),
            "site_name": site_name,
        }

        # Get description
        desc_meta = soup.find("meta", attrs={"name": "description"})
        if desc_meta:
            metadata["description"] = desc_meta.get("content")

        return WebContent(
            text=text,
            title=title,
            url=url,
            site_name=site_name,
            published_at=published_at,
            metadata=metadata,
        )

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # Remove lines that are likely navigation/buttons
                if len(line) < 3:
                    continue
                cleaned_lines.append(line)

        # Join and remove excessive newlines
        text = "\n".join(cleaned_lines)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()


# Singleton instance
web_processor = WebProcessor()
