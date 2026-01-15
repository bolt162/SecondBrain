from typing import List, Optional
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.services.embeddings import embedding_service


@dataclass
class ChunkData:
    """Represents a chunk of text with metadata."""
    text: str
    chunk_index: int
    char_start: int
    char_end: int
    token_count: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    time_start_ms: Optional[int] = None
    time_end_ms: Optional[int] = None
    metadata: Optional[dict] = None


class ChunkingService:
    """Service for splitting documents into chunks."""

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size * 4,  # Approximate chars
            chunk_overlap=settings.chunk_overlap * 4,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_text(
        self,
        text: str,
        page_boundaries: Optional[List[tuple]] = None,
    ) -> List[ChunkData]:
        """
        Split text into chunks.

        Args:
            text: The full text to chunk
            page_boundaries: Optional list of (page_num, char_start, char_end) tuples

        Returns:
            List of ChunkData objects
        """
        if not text.strip():
            return []

        # Use langchain splitter for initial splits
        splits = self.splitter.split_text(text)

        chunks = []
        current_pos = 0

        for idx, split_text in enumerate(splits):
            # Find the position of this chunk in the original text
            char_start = text.find(split_text, current_pos)
            if char_start == -1:
                char_start = current_pos
            char_end = char_start + len(split_text)
            current_pos = char_start + 1

            # Determine page numbers if boundaries provided
            page_start = None
            page_end = None
            if page_boundaries:
                for page_num, p_start, p_end in page_boundaries:
                    if p_start <= char_start < p_end:
                        page_start = page_num
                    if p_start < char_end <= p_end:
                        page_end = page_num
                if page_start and not page_end:
                    page_end = page_start

            # Count tokens
            token_count = embedding_service.count_tokens(split_text)

            chunks.append(ChunkData(
                text=split_text,
                chunk_index=idx,
                char_start=char_start,
                char_end=char_end,
                token_count=token_count,
                page_start=page_start,
                page_end=page_end,
            ))

        return chunks

    def chunk_audio_segments(
        self,
        segments: List[dict],
        target_duration_ms: int = 60000,  # 1 minute chunks
    ) -> List[ChunkData]:
        """
        Chunk audio transcript segments into larger chunks.

        Args:
            segments: List of {"text": str, "start_ms": int, "end_ms": int}
            target_duration_ms: Target duration per chunk in milliseconds

        Returns:
            List of ChunkData objects
        """
        if not segments:
            return []

        chunks = []
        current_texts = []
        current_start_ms = None
        current_end_ms = None
        chunk_index = 0
        char_offset = 0

        for segment in segments:
            seg_text = segment.get("text", "").strip()
            seg_start = segment.get("start_ms", 0)
            seg_end = segment.get("end_ms", seg_start)

            if not seg_text:
                continue

            if current_start_ms is None:
                current_start_ms = seg_start

            current_texts.append(seg_text)
            current_end_ms = seg_end

            # Check if we've reached target duration
            duration = current_end_ms - current_start_ms
            if duration >= target_duration_ms:
                # Create chunk
                chunk_text = " ".join(current_texts)
                token_count = embedding_service.count_tokens(chunk_text)

                chunks.append(ChunkData(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    char_start=char_offset,
                    char_end=char_offset + len(chunk_text),
                    token_count=token_count,
                    time_start_ms=current_start_ms,
                    time_end_ms=current_end_ms,
                ))

                char_offset += len(chunk_text) + 1
                chunk_index += 1
                current_texts = []
                current_start_ms = None
                current_end_ms = None

        # Handle remaining segments
        if current_texts:
            chunk_text = " ".join(current_texts)
            token_count = embedding_service.count_tokens(chunk_text)

            chunks.append(ChunkData(
                text=chunk_text,
                chunk_index=chunk_index,
                char_start=char_offset,
                char_end=char_offset + len(chunk_text),
                token_count=token_count,
                time_start_ms=current_start_ms,
                time_end_ms=current_end_ms,
            ))

        return chunks


# Singleton instance
chunking_service = ChunkingService()
