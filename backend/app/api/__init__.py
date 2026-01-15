from fastapi import APIRouter

from app.api import ingest, chat, documents

api_router = APIRouter()

api_router.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
