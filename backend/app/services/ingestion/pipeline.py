import os
import uuid
import hashlib
import aiofiles
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import (
    Document, Chunk, ChunkEmbedding, IngestionJob,
    SourceType, JobStatus, JobStage
)
from app.services.embeddings import embedding_service
from app.services.chunking import chunking_service
from app.services.ingestion.audio import audio_processor
from app.services.ingestion.documents import document_processor
from app.services.ingestion.web import web_processor


class IngestionPipeline:
    """Orchestrates the ingestion of various content types."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_text(
        self,
        user_id: UUID,
        text: str,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> Document:
        """Ingest plain text content."""
        content_hash = hashlib.sha256(text.encode()).hexdigest()

        # Create document
        doc = Document(
            user_id=user_id,
            source_type=SourceType.TEXT,
            title=title or text[:100].strip() + "..." if len(text) > 100 else text.strip(),
            content_text=text,
            content_hash=content_hash,
            created_at=created_at or datetime.now(timezone.utc),
            status=JobStatus.RUNNING,
        )
        self.db.add(doc)
        await self.db.flush()

        # Create ingestion job
        job = IngestionJob(
            user_id=user_id,
            document_id=doc.id,
            status=JobStatus.RUNNING,
            stage=JobStage.RECEIVED,
        )
        self.db.add(job)
        await self.db.flush()

        try:
            # Chunk the text
            await self._update_job_stage(job, JobStage.CHUNKED)
            chunks_data = chunking_service.chunk_text(text)

            # Create chunks and embeddings
            await self._update_job_stage(job, JobStage.EMBEDDED)
            await self._create_chunks_with_embeddings(doc, user_id, chunks_data)

            # Mark complete
            await self._update_job_stage(job, JobStage.INDEXED)
            job.status = JobStatus.COMPLETED
            doc.status = JobStatus.COMPLETED
            doc.ingested_at = datetime.now(timezone.utc)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            doc.status = JobStatus.FAILED
            raise

        await self.db.commit()
        return doc

    async def ingest_url(self, user_id: UUID, url: str) -> Document:
        """Ingest content from a URL."""
        # Fetch and extract content
        web_content = await web_processor.fetch_and_extract(url)
        content_hash = hashlib.sha256(web_content.text.encode()).hexdigest()

        # Create document
        doc = Document(
            user_id=user_id,
            source_type=SourceType.WEB,
            title=web_content.title or url,
            source_uri=url,
            content_text=web_content.text,
            content_hash=content_hash,
            created_at=web_content.published_at or datetime.now(timezone.utc),
            fetched_at=datetime.now(timezone.utc),
            metadata_=web_content.metadata,
            status=JobStatus.RUNNING,
        )
        self.db.add(doc)
        await self.db.flush()

        # Create ingestion job
        job = IngestionJob(
            user_id=user_id,
            document_id=doc.id,
            status=JobStatus.RUNNING,
            stage=JobStage.EXTRACTED,
        )
        self.db.add(job)
        await self.db.flush()

        try:
            # Chunk the text
            await self._update_job_stage(job, JobStage.CHUNKED)
            chunks_data = chunking_service.chunk_text(web_content.text)

            # Create chunks and embeddings
            await self._update_job_stage(job, JobStage.EMBEDDED)
            await self._create_chunks_with_embeddings(doc, user_id, chunks_data)

            # Mark complete
            await self._update_job_stage(job, JobStage.INDEXED)
            job.status = JobStatus.COMPLETED
            doc.status = JobStatus.COMPLETED
            doc.ingested_at = datetime.now(timezone.utc)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            doc.status = JobStatus.FAILED
            raise

        await self.db.commit()
        return doc

    async def ingest_file(
        self,
        user_id: UUID,
        file_path: str,
        original_filename: str,
        source_type: SourceType,
        created_at: Optional[datetime] = None,
    ) -> Document:
        """Ingest a file (audio or document)."""
        # Determine file type and process accordingly
        if source_type == SourceType.AUDIO:
            return await self._ingest_audio(user_id, file_path, original_filename, created_at)
        elif source_type in {SourceType.PDF, SourceType.MARKDOWN}:
            return await self._ingest_document(user_id, file_path, original_filename, source_type, created_at)
        else:
            # Treat as text
            async with aiofiles.open(file_path, "r") as f:
                text = await f.read()
            return await self.ingest_text(user_id, text, title=original_filename, created_at=created_at)

    async def _ingest_audio(
        self,
        user_id: UUID,
        file_path: str,
        original_filename: str,
        created_at: Optional[datetime] = None,
    ) -> Document:
        """Process and ingest an audio file."""
        # Get file hash for idempotency
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        content_hash = hashlib.sha256(content).hexdigest()

        # Save file to uploads directory
        upload_dir = os.path.join(settings.upload_dir, str(user_id), "audio")
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(original_filename)[1]
        stored_filename = f"{uuid.uuid4()}{ext}"
        stored_path = os.path.join(upload_dir, stored_filename)

        async with aiofiles.open(stored_path, "wb") as f:
            await f.write(content)

        # Create document
        doc = Document(
            user_id=user_id,
            source_type=SourceType.AUDIO,
            title=original_filename,
            source_uri=stored_path,
            original_filename=original_filename,
            content_hash=content_hash,
            created_at=created_at or datetime.now(timezone.utc),
            status=JobStatus.RUNNING,
        )
        self.db.add(doc)
        await self.db.flush()

        # Create ingestion job
        job = IngestionJob(
            user_id=user_id,
            document_id=doc.id,
            status=JobStatus.RUNNING,
            stage=JobStage.RECEIVED,
        )
        self.db.add(job)
        await self.db.flush()

        try:
            # Transcribe audio
            await self._update_job_stage(job, JobStage.EXTRACTED)
            transcript = await audio_processor.transcribe(stored_path)

            # Update document with transcript
            doc.content_text = transcript.text
            doc.metadata_ = {
                "duration_ms": transcript.duration_ms,
                "language": transcript.language,
                "segment_count": len(transcript.segments),
            }

            # Chunk based on audio segments
            await self._update_job_stage(job, JobStage.CHUNKED)
            chunks_data = chunking_service.chunk_audio_segments(transcript.segments)

            # Create chunks with embeddings
            await self._update_job_stage(job, JobStage.EMBEDDED)
            await self._create_chunks_with_embeddings(
                doc, user_id, chunks_data,
                base_time=created_at or datetime.now(timezone.utc)
            )

            # Mark complete
            await self._update_job_stage(job, JobStage.INDEXED)
            job.status = JobStatus.COMPLETED
            doc.status = JobStatus.COMPLETED
            doc.ingested_at = datetime.now(timezone.utc)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            doc.status = JobStatus.FAILED
            raise

        await self.db.commit()
        return doc

    async def _ingest_document(
        self,
        user_id: UUID,
        file_path: str,
        original_filename: str,
        source_type: SourceType,
        created_at: Optional[datetime] = None,
    ) -> Document:
        """Process and ingest a document file."""
        # Get file hash
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        content_hash = hashlib.sha256(content).hexdigest()

        # Save file to uploads directory
        upload_dir = os.path.join(settings.upload_dir, str(user_id), "documents")
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(original_filename)[1]
        stored_filename = f"{uuid.uuid4()}{ext}"
        stored_path = os.path.join(upload_dir, stored_filename)

        async with aiofiles.open(stored_path, "wb") as f:
            await f.write(content)

        # Extract document content
        extracted = await document_processor.process(stored_path)

        # Create document
        doc = Document(
            user_id=user_id,
            source_type=source_type,
            title=extracted.title or original_filename,
            source_uri=stored_path,
            original_filename=original_filename,
            content_text=extracted.text,
            content_hash=content_hash,
            created_at=created_at or datetime.now(timezone.utc),
            metadata_=extracted.metadata,
            status=JobStatus.RUNNING,
        )
        self.db.add(doc)
        await self.db.flush()

        # Create ingestion job
        job = IngestionJob(
            user_id=user_id,
            document_id=doc.id,
            status=JobStatus.RUNNING,
            stage=JobStage.EXTRACTED,
        )
        self.db.add(job)
        await self.db.flush()

        try:
            # Chunk the document
            await self._update_job_stage(job, JobStage.CHUNKED)
            chunks_data = chunking_service.chunk_text(
                extracted.text,
                page_boundaries=extracted.page_boundaries
            )

            # Create chunks with embeddings
            await self._update_job_stage(job, JobStage.EMBEDDED)
            await self._create_chunks_with_embeddings(doc, user_id, chunks_data)

            # Mark complete
            await self._update_job_stage(job, JobStage.INDEXED)
            job.status = JobStatus.COMPLETED
            doc.status = JobStatus.COMPLETED
            doc.ingested_at = datetime.now(timezone.utc)

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            doc.status = JobStatus.FAILED
            raise

        await self.db.commit()
        return doc

    async def _create_chunks_with_embeddings(
        self,
        doc: Document,
        user_id: UUID,
        chunks_data: list,
        base_time: Optional[datetime] = None,
    ):
        """Create chunk records and their embeddings."""
        if not chunks_data:
            return

        # Batch embed all chunks
        texts = [c.text for c in chunks_data]
        embeddings = await embedding_service.embed_texts(texts)

        for chunk_data, embedding in zip(chunks_data, embeddings):
            # Calculate time_start/time_end for audio chunks
            time_start = None
            time_end = None
            if chunk_data.time_start_ms is not None and base_time:
                from datetime import timedelta
                time_start = base_time + timedelta(milliseconds=chunk_data.time_start_ms)
                time_end = base_time + timedelta(milliseconds=chunk_data.time_end_ms)

            # Create chunk
            chunk = Chunk(
                document_id=doc.id,
                user_id=user_id,
                chunk_index=chunk_data.chunk_index,
                text=chunk_data.text,
                token_count=chunk_data.token_count,
                char_start=chunk_data.char_start,
                char_end=chunk_data.char_end,
                page_start=chunk_data.page_start,
                page_end=chunk_data.page_end,
                time_start=time_start,
                time_end=time_end,
                source_offset_ms_start=chunk_data.time_start_ms,
                source_offset_ms_end=chunk_data.time_end_ms,
                chunk_metadata=chunk_data.metadata,
            )
            self.db.add(chunk)
            await self.db.flush()

            # Create embedding
            chunk_embedding = ChunkEmbedding(
                chunk_id=chunk.id,
                embedding=embedding,
                embedding_model=settings.embedding_model,
            )
            self.db.add(chunk_embedding)

    async def _update_job_stage(self, job: IngestionJob, stage: JobStage):
        """Update the job stage."""
        job.stage = stage
        job.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

    async def get_job_status(self, job_id: UUID) -> Optional[IngestionJob]:
        """Get the status of an ingestion job."""
        result = await self.db.execute(
            select(IngestionJob).where(IngestionJob.id == job_id)
        )
        return result.scalar_one_or_none()
