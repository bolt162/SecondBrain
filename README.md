# SecondBrain - AI Knowledge Companion

A personal AI companion that can ingest, understand, and reason about your information. Ask questions and get accurate, cited answers from your documents, audio recordings, and web content.

## Features

- **Multi-modal Ingestion**: Upload PDFs, audio files (MP3, M4A), markdown, or add URLs
- **Intelligent Q&A**: Ask natural language questions and get synthesized answers
- **Temporal Queries**: Ask time-based questions like "What did I discuss last Tuesday?"
- **Citations**: Every answer includes source references with page/time information
- **Streaming Responses**: Real-time token-by-token response display

## Tech Stack

### Backend
- **FastAPI** - Async Python web framework
- **PostgreSQL + pgvector** - Database with vector similarity search
- **OpenAI Whisper** - Audio transcription
- **OpenAI Embeddings** - Text embeddings (text-embedding-3-small)
- **Google Gemini** - LLM for answer generation (gemini-1.5-flash)

### Frontend
- **React + TypeScript** - Modern UI framework
- **Tailwind CSS** - Utility-first styling
- **Vite** - Fast build tool

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key (for Whisper transcription and embeddings)
- Google API key (for Gemini LLM)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd SecondBrain
```

2. Create environment file:
```bash
cp .env.example .env
# Edit .env and add your API keys
```

3. Start with Docker Compose:
```bash
docker-compose up --build
```

4. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL with pgvector (Docker)
docker run -d --name pgvector -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=secondbrain -p 5432:5432 pgvector/pgvector:pg16

# Run the server
uvicorn app.main:app --reload
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Endpoints

### Ingestion
- `POST /v1/ingest/text` - Ingest plain text
- `POST /v1/ingest/url` - Ingest web content
- `POST /v1/ingest/file` - Upload and ingest files

### Chat
- `POST /v1/chat` - Send message and get response
- `POST /v1/chat/stream` - Send message with streaming response
- `GET /v1/chat/conversations` - List conversations

### Documents
- `GET /v1/documents` - List all documents
- `GET /v1/documents/{id}` - Get document details
- `DELETE /v1/documents/{id}` - Delete a document

## Deployment

### Supabase + Railway/Render

1. **Database (Supabase)**:
   - Create a new project at supabase.com
   - Enable pgvector extension: `CREATE EXTENSION vector;`
   - Get connection string from Settings > Database

2. **Backend (Railway/Render)**:
   - Connect your repository
   - Set environment variables:
     - `DATABASE_URL` (from Supabase)
     - `OPENAI_API_KEY`
     - `GOOGLE_API_KEY`
   - Deploy from `backend/` directory

3. **Frontend (Vercel)**:
   - Import from GitHub
   - Set build directory to `frontend/`
   - Configure API proxy to backend URL

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  - Chat Interface                                   │
│  - File Upload                                      │
│  - Document Management                              │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP/SSE
┌─────────────────▼───────────────────────────────────┐
│                  Backend (FastAPI)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Ingestion  │  │  Retrieval  │  │     LLM     │  │
│  │  Pipeline   │  │   Service   │  │   Service   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│              PostgreSQL + pgvector                   │
│  - Documents & Chunks                               │
│  - Vector Embeddings (HNSW index)                   │
│  - Full-text Search (tsvector)                      │
└─────────────────────────────────────────────────────┘
```

## License

MIT
