# SecondBrain

A personal AI knowledge companion that ingests, understands, and reasons about your information. Upload documents, audio files, or notes and ask natural language questions to get intelligent, contextual answers.

## Live Demo

**[View Live Application](https://second-brain-seven-kappa.vercel.app/)**

## Screenshots

![SecondBrain Chat Interface](screenshots/demo-1.png)**  **
*Main chat interface with document sidebar*

<img src="screenshots/demo-2.png" width="50" height="100"/>**  **
*File upload and document management*

## System Architecture

For detailed system design and architecture diagrams, see: [System Design Document](./SYSTEM_DESIGN.pdf)

## Features

- **Multi-modal Ingestion**: Upload PDFs, audio files (MP3, M4A, WAV), markdown, or plain text notes
- **Intelligent Q&A**: Ask natural language questions and get synthesized answers from your knowledge base
- **Streaming Responses**: Real-time token-by-token response display for better UX
- **Document Management**: View, manage, and delete uploaded documents
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Technology Stack

### Backend

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Chosen for its high performance async support, automatic OpenAPI documentation, and native Python type hints integration. Ideal for building AI/ML APIs that require async operations. |
| **PostgreSQL + pgvector** | PostgreSQL provides robust relational data storage, while pgvector extension enables efficient vector similarity search using HNSW indexing - critical for semantic search over document embeddings. |
| **SQLAlchemy (Async)** | Async ORM that integrates seamlessly with FastAPI's async architecture, providing type-safe database operations without blocking I/O. |
| **OpenAI Embeddings** | Using `text-embedding-3-small` model for generating high-quality 1536-dimensional text embeddings. Chosen for its excellent price-to-performance ratio and semantic understanding. |
| **OpenAI Whisper** | Industry-leading speech-to-text model for accurate audio transcription, supporting multiple languages and audio formats. |
| **OpenAI GPT-4o-mini** | Fast, cost-effective LLM for answer generation. Provides high-quality responses with good context understanding at lower latency than larger models. |

### Frontend

| Technology | Purpose |
|------------|---------|
| **React 18** | Modern UI library with hooks and concurrent features. Chosen for its component-based architecture, large ecosystem, and excellent developer experience. |
| **TypeScript** | Adds static typing to JavaScript, catching errors at compile time and improving code maintainability and IDE support. |
| **Tailwind CSS** | Utility-first CSS framework enabling rapid UI development without context-switching to separate CSS files. Produces minimal production bundles. |
| **Vite** | Next-generation build tool offering instant HMR (Hot Module Replacement) and optimized production builds. Significantly faster than traditional bundlers like Webpack. |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| **Supabase** | Managed PostgreSQL with pgvector support, eliminating the need to self-host and manage database infrastructure. Provides connection pooling for serverless environments. |
| **Railway** | Simple container-based deployment platform for the FastAPI backend. Handles SSL, scaling, and environment management automatically. |
| **Vercel** | Optimized for React/Vite deployments with global CDN, automatic HTTPS, and seamless GitHub integration for CI/CD. |

## Project Structure

```
SecondBrain/
├── backend/
│   ├── app/
│   │   ├── api/           # API route handlers
│   │   ├── db/            # Database configuration
│   │   ├── models/        # SQLAlchemy models & Pydantic schemas
│   │   └── services/      # Business logic (ingestion, retrieval, LLM)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   ├── services/      # API client
│   │   └── types/         # TypeScript type definitions
│   └── package.json
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL with pgvector extension (or Supabase account)
- OpenAI API key

### Local Development

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/secondbrain"
export OPENAI_API_KEY="your-api-key"

# Run the server
uvicorn app.main:app --reload
```

#### Frontend

```bash
cd frontend
npm install

# For local development (API at localhost:8000)
npm run dev

# For production build
npm run build
```

### Environment Variables

#### Backend
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key for embeddings and LLM |

#### Frontend
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL (e.g., `https://api.example.com`) |

## API Endpoints

### Ingestion
- `POST /v1/ingest/text` - Ingest plain text content
- `POST /v1/ingest/file` - Upload and ingest files (PDF, audio, markdown)

### Chat
- `POST /v1/chat` - Send message and get response
- `POST /v1/chat/stream` - Send message with streaming response (SSE)
- `GET /v1/chat/conversations` - List all conversations

### Documents
- `GET /v1/documents` - List all documents
- `GET /v1/documents/{id}` - Get document details
- `DELETE /v1/documents/{id}` - Delete a document

## Deployment

### Database (Supabase)
1. Create a new project at [supabase.com](https://supabase.com)
2. pgvector extension is pre-enabled
3. Copy the connection string from Settings > Database > Connection Pooling

### Backend (Railway)
1. Connect your GitHub repository
2. Set root directory to `backend`
3. Add environment variables (`DATABASE_URL`, `OPENAI_API_KEY`)
4. Deploy

### Frontend (Vercel)
1. Import from GitHub
2. Set root directory to `frontend`
3. Add environment variable `VITE_API_URL` with your Railway backend URL
4. Deploy
