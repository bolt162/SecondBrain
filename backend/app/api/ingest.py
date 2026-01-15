import os
import tempfile
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.models import SourceType, Document, IngestionJob, User
from app.models.schemas import (
    IngestTextRequest,
    IngestURLRequest,
    IngestionJobResponse,
    DocumentResponse,
)
from app.services.ingestion.pipeline import IngestionPipeline
from app.api.dependencies import get_current_user_id

router = APIRouter()


@router.post("/text", response_model=DocumentResponse)
async def ingest_text(
    request: IngestTextRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Ingest plain text content."""
    pipeline = IngestionPipeline(db)

    try:
        doc = await pipeline.ingest_text(
            user_id=user_id,
            text=request.text,
            title=request.title,
            created_at=request.created_at,
        )
        return DocumentResponse.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/url", response_model=DocumentResponse)
async def ingest_url(
    request: IngestURLRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Ingest content from a URL."""
    pipeline = IngestionPipeline(db)

    try:
        doc = await pipeline.ingest_url(
            user_id=user_id,
            url=request.url,
        )
        return DocumentResponse.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/file", response_model=DocumentResponse)
async def ingest_file(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    created_at: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Ingest a file (audio, PDF, markdown, etc.).

    - **file**: The file to upload
    - **source_type**: Type of file (audio, pdf, markdown, text)
    - **created_at**: Optional creation timestamp (ISO format)
    """
    # Validate source type
    try:
        source_type_enum = SourceType(source_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type. Must be one of: {[s.value for s in SourceType]}"
        )

    # Parse created_at if provided
    created_at_dt = None
    if created_at:
        try:
            created_at_dt = datetime.fromisoformat(created_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid created_at format. Use ISO format.")

    # Save uploaded file temporarily
    ext = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipeline = IngestionPipeline(db)
        doc = await pipeline.ingest_file(
            user_id=user_id,
            file_path=tmp_path,
            original_filename=file.filename or "uploaded_file",
            source_type=source_type_enum,
            created_at=created_at_dt,
        )
        return DocumentResponse.model_validate(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/jobs/{job_id}", response_model=IngestionJobResponse)
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get the status of an ingestion job."""
    from sqlalchemy import select

    result = await db.execute(
        select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.user_id == user_id
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return IngestionJobResponse.model_validate(job)
