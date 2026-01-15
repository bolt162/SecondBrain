import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, text, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.models.models import Chunk, ChunkEmbedding, Document
from app.models.schemas import RetrievedChunk
from app.services.embeddings import embedding_service


class TemporalParser:
    """Parse temporal expressions from queries."""

    @staticmethod
    def parse_time_expression(
        query: str,
        timezone: str = "UTC",
        reference_time: Optional[datetime] = None,
    ) -> Tuple[str, Optional[datetime], Optional[datetime]]:
        """
        Extract time range from query if present.

        Returns:
            Tuple of (cleaned_query, time_start, time_end)
        """
        if reference_time is None:
            reference_time = datetime.utcnow()

        patterns = [
            # "last Tuesday", "last Monday", etc.
            (r"\blast\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
             lambda m: TemporalParser._get_last_weekday(m.group(1), reference_time)),
            # "yesterday"
            (r"\byesterday\b",
             lambda m: (reference_time - timedelta(days=1), reference_time)),
            # "last week"
            (r"\blast\s+week\b",
             lambda m: (reference_time - timedelta(days=7), reference_time)),
            # "last month"
            (r"\blast\s+month\b",
             lambda m: (reference_time - timedelta(days=30), reference_time)),
            # "last N days"
            (r"\blast\s+(\d+)\s+days?\b",
             lambda m: (reference_time - timedelta(days=int(m.group(1))), reference_time)),
            # "in November", "in January", etc.
            (r"\bin\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b",
             lambda m: TemporalParser._get_month_range(m.group(1), reference_time)),
            # "this week"
            (r"\bthis\s+week\b",
             lambda m: (reference_time - timedelta(days=reference_time.weekday()), reference_time)),
            # "today"
            (r"\btoday\b",
             lambda m: (reference_time.replace(hour=0, minute=0, second=0), reference_time)),
        ]

        for pattern, handler in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                time_range = handler(match)
                if time_range:
                    cleaned_query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()
                    return cleaned_query, time_range[0], time_range[1]

        return query, None, None

    @staticmethod
    def _get_last_weekday(
        weekday_name: str,
        reference: datetime
    ) -> Tuple[datetime, datetime]:
        """Get the date range for 'last Monday', 'last Tuesday', etc."""
        weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        target_weekday = weekdays.get(weekday_name.lower(), 0)
        days_back = (reference.weekday() - target_weekday) % 7
        if days_back == 0:
            days_back = 7  # "last Monday" when today is Monday means a week ago

        target_date = reference - timedelta(days=days_back)
        start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        return start, end

    @staticmethod
    def _get_month_range(
        month_name: str,
        reference: datetime
    ) -> Tuple[datetime, datetime]:
        """Get the date range for 'in January', 'in November', etc."""
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        target_month = months.get(month_name.lower(), 1)

        # Assume current year, or previous year if month is in the future
        year = reference.year
        if target_month > reference.month:
            year -= 1

        # Get start and end of month
        start = datetime(year, target_month, 1)
        if target_month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end = datetime(year, target_month + 1, 1) - timedelta(seconds=1)

        return start, end


class RetrievalService:
    """Hybrid retrieval service combining vector and full-text search."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.temporal_parser = TemporalParser()

    async def retrieve(
        self,
        user_id: UUID,
        query: str,
        timezone: str = "UTC",
        top_k: int = 10,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> List[RetrievedChunk]:
        """
        Perform hybrid retrieval combining vector and full-text search.

        Args:
            user_id: User ID for filtering
            query: The search query
            timezone: User's timezone for temporal parsing
            top_k: Number of results to return
            vector_weight: Weight for vector similarity scores
            text_weight: Weight for full-text search scores

        Returns:
            List of RetrievedChunk objects
        """
        # Parse temporal expressions
        cleaned_query, time_start, time_end = self.temporal_parser.parse_time_expression(
            query, timezone
        )

        # Get query embedding
        query_embedding = await embedding_service.embed_text(cleaned_query)

        # Perform vector search
        vector_results = await self._vector_search(
            user_id, query_embedding, top_k * 3, time_start, time_end
        )

        # Perform full-text search
        text_results = await self._fulltext_search(
            user_id, cleaned_query, top_k * 3, time_start, time_end
        )

        # Merge and rerank results
        merged = self._merge_results(
            vector_results, text_results,
            vector_weight, text_weight
        )

        # Return top_k
        return merged[:top_k]

    async def _vector_search(
        self,
        user_id: UUID,
        query_embedding: List[float],
        limit: int,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
    ) -> List[Tuple[RetrievedChunk, float]]:
        """Perform vector similarity search."""
        # Build the query
        query = (
            select(
                Chunk,
                Document,
                ChunkEmbedding.embedding.cosine_distance(query_embedding).label("distance")
            )
            .join(ChunkEmbedding, Chunk.id == ChunkEmbedding.chunk_id)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.user_id == user_id)
        )

        # Add temporal filter
        if time_start and time_end:
            query = query.where(
                or_(
                    # Chunks with time range overlapping query range
                    and_(
                        Chunk.time_start.isnot(None),
                        Chunk.time_start <= time_end,
                        Chunk.time_end >= time_start
                    ),
                    # Chunks without time range, use document created_at
                    and_(
                        Chunk.time_start.is_(None),
                        Document.created_at >= time_start,
                        Document.created_at <= time_end
                    )
                )
            )

        query = query.order_by("distance").limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        chunks = []
        for chunk, doc, distance in rows:
            # Convert distance to similarity score (1 - distance for cosine)
            score = 1 - distance

            retrieved = RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                document_title=doc.title,
                source_uri=doc.source_uri,
                source_type=doc.source_type,
                text=chunk.text,
                score=score,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                time_start=chunk.time_start,
                time_end=chunk.time_end,
            )
            chunks.append((retrieved, score))

        return chunks

    async def _fulltext_search(
        self,
        user_id: UUID,
        query: str,
        limit: int,
        time_start: Optional[datetime] = None,
        time_end: Optional[datetime] = None,
    ) -> List[Tuple[RetrievedChunk, float]]:
        """Perform full-text search using PostgreSQL tsvector."""
        # Prepare the search query for tsquery
        search_terms = " & ".join(query.split())

        # Build the query using ts_rank
        stmt = (
            select(
                Chunk,
                Document,
                func.ts_rank(Chunk.tsv, func.to_tsquery("english", search_terms)).label("rank")
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.user_id == user_id)
            .where(Chunk.tsv.op("@@")(func.to_tsquery("english", search_terms)))
        )

        # Add temporal filter
        if time_start and time_end:
            stmt = stmt.where(
                or_(
                    and_(
                        Chunk.time_start.isnot(None),
                        Chunk.time_start <= time_end,
                        Chunk.time_end >= time_start
                    ),
                    and_(
                        Chunk.time_start.is_(None),
                        Document.created_at >= time_start,
                        Document.created_at <= time_end
                    )
                )
            )

        stmt = stmt.order_by(text("rank DESC")).limit(limit)

        try:
            result = await self.db.execute(stmt)
            rows = result.all()
        except Exception:
            # If full-text search fails (e.g., invalid query), return empty
            return []

        chunks = []
        for chunk, doc, rank in rows:
            # Normalize rank to 0-1 range (ts_rank typically returns small values)
            score = min(rank * 10, 1.0)  # Scale up but cap at 1

            retrieved = RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                document_title=doc.title,
                source_uri=doc.source_uri,
                source_type=doc.source_type,
                text=chunk.text,
                score=score,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                time_start=chunk.time_start,
                time_end=chunk.time_end,
            )
            chunks.append((retrieved, score))

        return chunks

    def _merge_results(
        self,
        vector_results: List[Tuple[RetrievedChunk, float]],
        text_results: List[Tuple[RetrievedChunk, float]],
        vector_weight: float,
        text_weight: float,
    ) -> List[RetrievedChunk]:
        """Merge and rerank results from both search methods."""
        # Create a dictionary to combine scores
        chunk_scores: dict = {}

        for chunk, score in vector_results:
            chunk_scores[chunk.chunk_id] = {
                "chunk": chunk,
                "vector_score": score,
                "text_score": 0.0,
            }

        for chunk, score in text_results:
            if chunk.chunk_id in chunk_scores:
                chunk_scores[chunk.chunk_id]["text_score"] = score
            else:
                chunk_scores[chunk.chunk_id] = {
                    "chunk": chunk,
                    "vector_score": 0.0,
                    "text_score": score,
                }

        # Calculate combined scores
        results = []
        for data in chunk_scores.values():
            combined_score = (
                data["vector_score"] * vector_weight +
                data["text_score"] * text_weight
            )
            chunk = data["chunk"]
            chunk.score = combined_score
            results.append(chunk)

        # Sort by combined score
        results.sort(key=lambda x: x.score, reverse=True)

        return results
