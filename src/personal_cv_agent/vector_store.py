"""Local vector database integration."""

from __future__ import annotations

import hashlib

from langchain_chroma import Chroma
from langchain_core.documents import Document

from personal_cv_agent.config import IngestionConfig
from personal_cv_agent.embeddings import build_embedding_model


class ChromaVectorStore:
    """Persist CV knowledge chunks into a local Chroma collection."""

    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.embedding_model = build_embedding_model(config)

    def upsert_documents(self, documents: list[Document]) -> Chroma:
        self.config.vector_db_dir.mkdir(parents=True, exist_ok=True)

        vector_store = Chroma(
            collection_name=self.config.collection_name,
            embedding_function=self.embedding_model,
            persist_directory=str(self.config.vector_db_dir),
        )

        ids = [
            self._document_id(document=document, fallback_index=index)
            for index, document in enumerate(documents)
        ]
        vector_store.add_documents(documents=documents, ids=ids)

        return vector_store

    def as_retriever(self):
        vector_store = Chroma(
            collection_name=self.config.collection_name,
            embedding_function=self.embedding_model,
            persist_directory=str(self.config.vector_db_dir),
        )
        return vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": self.config.retrieval_k,
                "fetch_k": self.config.retrieval_fetch_k,
                "lambda_mult": self.config.retrieval_lambda_mult,
            },
        )

    @staticmethod
    def _document_id(document: Document, fallback_index: int) -> str:
        """Create stable-ish IDs from source metadata.

        Stable IDs make the vector store easier to reason about during repeated
        ETL runs. If a source page or start index is missing, the fallback still
        keeps the ingestion process deterministic within the current batch.
        """

        source_file = document.metadata.get("source_file", "unknown-source")
        page = document.metadata.get("page", "unknown-page")
        start_index = document.metadata.get("start_index", fallback_index)
        source_type = document.metadata.get("source_type", "unknown-type")
        content_hash = hashlib.sha1(document.page_content.encode("utf-8")).hexdigest()[:12]
        return f"{source_type}:{source_file}:page-{page}:char-{start_index}:{content_hash}"
