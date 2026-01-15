from typing import List, AsyncGenerator, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import RetrievedChunk, Citation


class LLMService:
    """Service for LLM-based answer generation using OpenAI GPT."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model

    def _build_context(self, chunks: List[RetrievedChunk]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            # Build source reference
            source_info = f"[Source {i}: {chunk.document_title}"
            if chunk.page_start:
                source_info += f", Page {chunk.page_start}"
                if chunk.page_end and chunk.page_end != chunk.page_start:
                    source_info += f"-{chunk.page_end}"
            if chunk.time_start:
                source_info += f", Time: {chunk.time_start.strftime('%Y-%m-%d %H:%M')}"
            source_info += "]"

            context_parts.append(f"{source_info}\n{chunk.text}")

        return "\n\n---\n\n".join(context_parts)

    def _build_citations(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        """Build citation objects from chunks."""
        citations = []

        for chunk in chunks:
            # Build page range string
            page_range = None
            if chunk.page_start:
                page_range = str(chunk.page_start)
                if chunk.page_end and chunk.page_end != chunk.page_start:
                    page_range += f"-{chunk.page_end}"

            # Build time range string
            time_range = None
            if chunk.time_start:
                time_range = chunk.time_start.strftime("%Y-%m-%d %H:%M")
                if chunk.time_end and chunk.time_end != chunk.time_start:
                    time_range += f" - {chunk.time_end.strftime('%H:%M')}"

            citations.append(Citation(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                title=chunk.document_title,
                source_uri=chunk.source_uri,
                source_type=chunk.source_type,
                page_range=page_range,
                time_range=time_range,
                text_snippet=chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
            ))

        return citations

    def _build_messages(
        self, query: str, context: str, conversation_history: Optional[List[dict]] = None
    ) -> List[dict]:
        """Build the messages array for OpenAI chat completion."""
        system_message = """You are a helpful AI assistant that answers questions based on the user's personal knowledge base.

IMPORTANT RULES:
1. Only answer based on the provided context. Do not make up information.
2. If the context doesn't contain enough information to answer, say "I don't have enough information about that."
3. Reference sources using [Source N] notation when citing specific information.
4. Be concise but thorough in your answers.
5. If the question is about something that happened at a specific time, mention the relevant dates/times from the sources.
6. Synthesize information from multiple sources when relevant."""

        messages = [{"role": "system", "content": system_message}]

        # Add conversation history if present
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current query with context
        user_message = f"""Based on the following context from my knowledge base, please answer my question.

CONTEXT:
{context}

QUESTION: {query}"""

        messages.append({"role": "user", "content": user_message})

        return messages

    async def generate_answer(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        conversation_history: Optional[List[dict]] = None,
    ) -> tuple[str, List[Citation]]:
        """
        Generate an answer using OpenAI GPT.

        Args:
            query: User's question
            chunks: Retrieved context chunks
            conversation_history: Optional previous messages

        Returns:
            Tuple of (answer_text, citations)
        """
        if not chunks:
            return "I don't have any information about that in my knowledge base.", []

        context = self._build_context(chunks)
        citations = self._build_citations(chunks)
        messages = self._build_messages(query, context, conversation_history)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )

        answer = response.choices[0].message.content
        return answer, citations

    async def generate_answer_stream(
        self,
        query: str,
        chunks: List[RetrievedChunk],
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate an answer with streaming.

        Yields:
            Tokens as they're generated
        """
        if not chunks:
            yield "I don't have any information about that in my knowledge base."
            return

        context = self._build_context(chunks)
        messages = self._build_messages(query, context, conversation_history)

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_citations_for_chunks(self, chunks: List[RetrievedChunk]) -> List[Citation]:
        """Get citations without generating an answer."""
        return self._build_citations(chunks)


# Singleton instance
llm_service = LLMService()
