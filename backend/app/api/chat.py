import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.models import Conversation, Message
from app.models.schemas import ChatRequest, ChatResponse, Citation, MessageResponse, ConversationResponse
from app.services.retrieval import RetrievalService
from app.services.llm import llm_service
from app.api.dependencies import get_current_user_id

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Send a message and get a response based on the knowledge base.

    - **message**: The user's question
    - **conversation_id**: Optional ID to continue an existing conversation
    - **timezone**: User's timezone for temporal queries (default: UTC)
    """
    # Get or create conversation
    conversation = None
    conversation_history = []

    if request.conversation_id:
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_id
            )
            .options(selectinload(Conversation.messages))
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Build conversation history
        for msg in conversation.messages:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })

    if not conversation:
        conversation = Conversation(
            user_id=user_id,
            title=request.message[:100] if len(request.message) > 100 else request.message,
        )
        db.add(conversation)
        await db.flush()

    # Retrieve relevant context
    retrieval_service = RetrievalService(db)
    chunks = await retrieval_service.retrieve(
        user_id=user_id,
        query=request.message,
        timezone=request.timezone,
        top_k=5,
    )

    # Generate answer
    answer, citations = await llm_service.generate_answer(
        query=request.message,
        chunks=chunks,
        conversation_history=conversation_history,
    )

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)

    # Save assistant message (use mode='json' to serialize UUIDs as strings)
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        citations=[c.model_dump(mode='json') for c in citations] if citations else None,
    )
    db.add(assistant_message)

    await db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant_message.id,
        content=answer,
        citations=citations,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """
    Send a message and stream the response token by token.

    Returns Server-Sent Events (SSE) with the response.
    """
    # Get or create conversation
    conversation = None
    conversation_history = []

    if request.conversation_id:
        result = await db.execute(
            select(Conversation)
            .where(
                Conversation.id == request.conversation_id,
                Conversation.user_id == user_id
            )
            .options(selectinload(Conversation.messages))
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        for msg in conversation.messages:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })

    if not conversation:
        conversation = Conversation(
            user_id=user_id,
            title=request.message[:100] if len(request.message) > 100 else request.message,
        )
        db.add(conversation)
        await db.flush()

    # Retrieve relevant context
    retrieval_service = RetrievalService(db)
    chunks = await retrieval_service.retrieve(
        user_id=user_id,
        query=request.message,
        timezone=request.timezone,
        top_k=5,
    )

    # Get citations
    citations = llm_service.get_citations_for_chunks(chunks)

    # Save user message and commit before streaming
    # (StreamingResponse runs after endpoint returns, so we need to persist first)
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_message)
    await db.commit()

    # Store IDs for use in generator (session objects may become detached)
    conversation_id = conversation.id

    async def generate():
        full_response = ""

        # Send initial metadata
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': str(conversation_id)})}\n\n"

        # Send citations first
        citations_data = [c.model_dump(mode='json') for c in citations]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations_data})}\n\n"

        # Stream the response
        async for token in llm_service.generate_answer_stream(
            query=request.message,
            chunks=chunks,
            conversation_history=conversation_history,
        ):
            full_response += token
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        # Save assistant message (use mode='json' to serialize UUIDs as strings)
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
            citations=[c.model_dump(mode='json') for c in citations] if citations else None,
        )
        db.add(assistant_message)
        await db.commit()

        # Send completion
        yield f"data: {json.dumps({'type': 'done', 'message_id': str(assistant_message.id)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """List all conversations for the current user."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .options(selectinload(Conversation.messages))
    )
    conversations = result.scalars().all()

    return [ConversationResponse.model_validate(conv) for conv in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Get a specific conversation with all messages."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse.model_validate(conversation)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        )
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    return {"status": "deleted", "conversation_id": str(conversation_id)}
