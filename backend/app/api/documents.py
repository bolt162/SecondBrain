from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.models import Document, Chunk, SourceType
from app.models.schemas import DocumentResponse, DocumentListResponse, ChunkResponse
from app.api.dependencies import get_current_user_id

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    source_type: Optional[SourceType] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all documents for the current user."""
    # Build query
    query = select(Document).where(Document.user_id == user_id)

    if source_type:
        query = query.where(Document.source_type == source_type)

    # Get total count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get documents
    query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific document by ID."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/chunks", response_model=list[ChunkResponse])
async def get_document_chunks(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get all chunks for a document."""
    # Verify document exists and belongs to user
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    doc = doc_result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get chunks
    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )
    chunks = result.scalars().all()

    return [ChunkResponse.model_validate(chunk) for chunk in chunks]


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a document and all its chunks."""
    # Verify document exists and belongs to user
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id
        )
    )
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete document (cascades to chunks and embeddings)
    await db.delete(doc)
    await db.commit()

    return {"status": "deleted", "document_id": str(document_id)}
