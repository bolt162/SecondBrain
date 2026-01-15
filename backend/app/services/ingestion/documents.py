import os
from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import markdown
from bs4 import BeautifulSoup


@dataclass
class ExtractedDocument:
    """Result of document extraction."""
    text: str
    title: Optional[str] = None
    page_boundaries: Optional[List[Tuple[int, int, int]]] = None  # (page_num, char_start, char_end)
    metadata: Optional[dict] = None


class DocumentProcessor:
    """Processor for document files (PDF, Markdown, Text)."""

    SUPPORTED_FORMATS = {".pdf", ".md", ".markdown", ".txt", ".text"}

    def is_supported(self, filename: str) -> bool:
        """Check if the file format is supported."""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.SUPPORTED_FORMATS

    async def process(self, file_path: str) -> ExtractedDocument:
        """
        Process a document file and extract text.

        Args:
            file_path: Path to the document file

        Returns:
            ExtractedDocument with text and metadata
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return await self._process_pdf(file_path)
        elif ext in {".md", ".markdown"}:
            return await self._process_markdown(file_path)
        else:
            return await self._process_text(file_path)

    async def _process_pdf(self, file_path: str) -> ExtractedDocument:
        """Extract text from PDF file."""
        try:
            import pdfplumber

            text_parts = []
            page_boundaries = []
            title = None
            metadata = {}
            char_offset = 0

            with pdfplumber.open(file_path) as pdf:
                metadata["page_count"] = len(pdf.pages)

                # Try to get title from metadata
                if pdf.metadata:
                    title = pdf.metadata.get("Title")
                    metadata["author"] = pdf.metadata.get("Author")
                    metadata["creator"] = pdf.metadata.get("Creator")
                    if pdf.metadata.get("CreationDate"):
                        metadata["created_date"] = pdf.metadata.get("CreationDate")

                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text = page.extract_text() or ""

                    if page_text.strip():
                        page_start = char_offset
                        text_parts.append(page_text)
                        char_offset += len(page_text) + 1  # +1 for newline
                        page_boundaries.append((page_num, page_start, char_offset - 1))

            full_text = "\n".join(text_parts)

            # If no title from metadata, try first line
            if not title and full_text.strip():
                first_line = full_text.strip().split("\n")[0]
                if len(first_line) < 200:
                    title = first_line

            return ExtractedDocument(
                text=full_text,
                title=title,
                page_boundaries=page_boundaries,
                metadata=metadata,
            )

        except Exception as e:
            # Fallback to PyPDF2
            return await self._process_pdf_fallback(file_path)

    async def _process_pdf_fallback(self, file_path: str) -> ExtractedDocument:
        """Fallback PDF processing using PyPDF2."""
        from PyPDF2 import PdfReader

        text_parts = []
        page_boundaries = []
        char_offset = 0

        reader = PdfReader(file_path)
        metadata = {
            "page_count": len(reader.pages),
        }

        # Get metadata
        if reader.metadata:
            metadata["title"] = reader.metadata.get("/Title")
            metadata["author"] = reader.metadata.get("/Author")

        for page_num, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            if page_text.strip():
                page_start = char_offset
                text_parts.append(page_text)
                char_offset += len(page_text) + 1
                page_boundaries.append((page_num, page_start, char_offset - 1))

        full_text = "\n".join(text_parts)
        title = metadata.get("title")

        if not title and full_text.strip():
            first_line = full_text.strip().split("\n")[0]
            if len(first_line) < 200:
                title = first_line

        return ExtractedDocument(
            text=full_text,
            title=title,
            page_boundaries=page_boundaries,
            metadata=metadata,
        )

    async def _process_markdown(self, file_path: str) -> ExtractedDocument:
        """Extract text from Markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Convert markdown to HTML then extract text
        html = markdown.markdown(content)
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")

        # Extract title from first heading
        title = None
        lines = content.strip().split("\n")
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        metadata = {
            "original_format": "markdown",
            "file_size_bytes": os.path.getsize(file_path),
        }

        return ExtractedDocument(
            text=text,
            title=title,
            metadata=metadata,
        )

    async def _process_text(self, file_path: str) -> ExtractedDocument:
        """Process plain text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Use first line as title if reasonable
        title = None
        if text.strip():
            first_line = text.strip().split("\n")[0]
            if len(first_line) < 200:
                title = first_line

        metadata = {
            "original_format": "text",
            "file_size_bytes": os.path.getsize(file_path),
        }

        return ExtractedDocument(
            text=text,
            title=title,
            metadata=metadata,
        )


# Singleton instance
document_processor = DocumentProcessor()
