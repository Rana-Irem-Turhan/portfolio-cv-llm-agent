"""End-to-end CV ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from personal_cv_agent.config import IngestionConfig
from personal_cv_agent.loaders import CVPdfLoader
from personal_cv_agent.portfolio_loader import PortfolioSourceLoader
from personal_cv_agent.transformers import CVDenseTextTransformer
from personal_cv_agent.vector_store import ChromaVectorStore


@dataclass(frozen=True)
class IngestionResult:
    """Summary returned after an ingestion run."""

    source_path: Path
    pages_loaded: int
    chunks_created: int
    vector_db_dir: Path
    collection_name: str


class CVIngestionPipeline:
    """Coordinate extract, transform, and load steps for CV knowledge."""

    def __init__(self, config: IngestionConfig | None = None) -> None:
        self.config = config or IngestionConfig.from_env()
        self.loader = CVPdfLoader()
        self.portfolio_loader = PortfolioSourceLoader()
        self.transformer = CVDenseTextTransformer(self.config)
        self.vector_store = ChromaVectorStore(self.config)

    def ingest_pdf(self, pdf_path: Path) -> IngestionResult:
        """Load a PDF CV, chunk it, embed it, and persist it in Chroma."""

        pages = self.loader.load(pdf_path)
        chunks = self.transformer.transform(pages)
        self.vector_store.upsert_documents(chunks)

        return IngestionResult(
            source_path=pdf_path.expanduser().resolve(),
            pages_loaded=len(pages),
            chunks_created=len(chunks),
            vector_db_dir=self.config.vector_db_dir.resolve(),
            collection_name=self.config.collection_name,
        )

    def ingest_sources(
        self,
        pdf_paths: list[Path] | None = None,
        portfolio_paths: list[Path] | None = None,
    ) -> IngestionResult:
        """Load CV PDFs and portfolio sources into the same vector collection."""

        source_documents = []

        for pdf_path in pdf_paths or []:
            source_documents.extend(self.loader.load(pdf_path))

        for portfolio_path in portfolio_paths or []:
            source_documents.extend(self.portfolio_loader.load(portfolio_path))

        chunks = self.transformer.transform(source_documents)
        self.vector_store.upsert_documents(chunks)

        first_source = (pdf_paths or portfolio_paths or [Path(".")])[0]
        return IngestionResult(
            source_path=first_source.expanduser().resolve(),
            pages_loaded=len(source_documents),
            chunks_created=len(chunks),
            vector_db_dir=self.config.vector_db_dir.resolve(),
            collection_name=self.config.collection_name,
        )
