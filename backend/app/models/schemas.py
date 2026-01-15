from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.models import SourceType, JobStatus, JobStage


# ============ User Schemas ============
class UserCreate(BaseModel):
    email: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Document Schemas ============
class DocumentCreate(BaseModel):
    title: Optional[str] = None
    source_type: SourceType
    content_text: Optional[str] = None
    source_uri: Optional[str] = None
    created_at: Optional[datetime] = None


class DocumentResponse(BaseModel):
    id: UUID
    user_id: UUID
    source_type: SourceType
    title: str
    source_uri: Optional[str]
    original_filename: Optional[str]
    status: JobStatus
    created_at: datetime
    ingested_at: Optional[datetime]
    metadata: Optional[dict] = Field(default=None, validation_alias="metadata_")

    class Config:
        from_attributes = True
        populate_by_name = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


# ============ Chunk Schemas ============
class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    token_count: Optional[int]
    page_start: Optional[int]
    page_end: Optional[int]
    time_start: Optional[datetime]
    time_end: Optional[datetime]
    source_offset_ms_start: Optional[int]
    source_offset_ms_end: Optional[int]

    class Config:
        from_attributes = True


# ============ Ingestion Schemas ============
class IngestTextRequest(BaseModel):
    title: Optional[str] = None
    text: str
    created_at: Optional[datetime] = None


class IngestURLRequest(BaseModel):
    url: str


class IngestionJobResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: JobStatus
    stage: JobStage
    error: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ Chat Schemas ============
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[UUID] = None
    timezone: str = "UTC"


class Citation(BaseModel):
    chunk_id: UUID
    document_id: UUID
    title: str
    source_uri: Optional[str]
    source_type: SourceType
    page_range: Optional[str]
    time_range: Optional[str]
    text_snippet: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    content: str
    citations: List[Citation]


class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    citations: Optional[List[Citation]]
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    title: Optional[str]
    created_at: datetime
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


# ============ Retrieval Schemas ============
class RetrievedChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    source_uri: Optional[str]
    source_type: SourceType
    text: str
    score: float
    page_start: Optional[int]
    page_end: Optional[int]
    time_start: Optional[datetime]
    time_end: Optional[datetime]
