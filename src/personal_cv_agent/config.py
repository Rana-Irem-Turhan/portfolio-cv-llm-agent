"""Configuration objects for the CV ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IngestionConfig:
    """Runtime settings for document extraction, transformation, and loading.

    The defaults are tuned for a dense 1-2 page CV. A CV has high information
    density: job titles, dates, companies, tools, achievements, and education
    often appear in compact sections where losing neighboring context hurts
    downstream generation quality.
    """

    vector_db_dir: Path = Path("./data/chroma")
    collection_name: str = "cv_knowledge_base"

    embedding_provider: str = "openai"
    openai_embedding_model: str = "text-embedding-3-small"
    huggingface_embedding_model: str = "BAAI/bge-small-en-v1.5"
    google_embedding_model: str = "gemini-embedding-001"

    # Chunking strategy:
    # 900 characters is small enough that a single chunk usually captures one
    # CV section or sub-section, but large enough to preserve complete bullet
    # groups and role context. This follows an ETL/DWH principle: preserve the
    # grain of source facts so retrieval does not separate a metric from the
    # role, company, technology stack, or date that gives it meaning.
    chunk_size: int = 900

    # 150 characters keeps section headers, role names, and adjacent bullet
    # context available across chunk boundaries without creating excessive
    # duplicate records in the vector store. The overlap acts like a controlled
    # slowly-changing context bridge rather than arbitrary duplication.
    chunk_overlap: int = 150

    retrieval_k: int = 10
    retrieval_fetch_k: int = 35
    retrieval_lambda_mult: float = 0.65

    @classmethod
    def from_env(cls) -> "IngestionConfig":
        """Create config from environment variables.

        This constructor exists to make dependency injection explicit when the
        project grows. Future web scrapers can reuse the same config object and
        vector-store destination.
        """

        import os

        return cls(
            vector_db_dir=Path(os.getenv("CV_AGENT_VECTOR_DB_DIR", "./data/chroma")),
            collection_name=os.getenv(
                "CV_AGENT_COLLECTION_NAME",
                "cv_knowledge_base",
            ),
            embedding_provider=os.getenv("CV_AGENT_EMBEDDING_PROVIDER", "openai"),
            openai_embedding_model=os.getenv(
                "CV_AGENT_OPENAI_EMBEDDING_MODEL",
                "text-embedding-3-small",
            ),
            huggingface_embedding_model=os.getenv(
                "CV_AGENT_HF_EMBEDDING_MODEL",
                "BAAI/bge-small-en-v1.5",
            ),
            google_embedding_model=os.getenv(
                "CV_AGENT_GOOGLE_EMBEDDING_MODEL",
                "gemini-embedding-001",
            ),
        )
