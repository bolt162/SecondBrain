import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/secondbrain"
    )
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )

    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")

    # App settings
    app_name: str = "SecondBrain"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # File storage
    upload_dir: str = os.getenv("UPLOAD_DIR", "./uploads")
    max_file_size_mb: int = 50

    # Embedding settings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # LLM settings
    llm_model: str = "gpt-4o-mini"
    max_context_tokens: int = 8000

    # Chunking settings
    chunk_size: int = 500
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
