"""Transformation layer: cleaning and semantic chunking."""

from __future__ import annotations

import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from personal_cv_agent.config import IngestionConfig


class CVDenseTextTransformer:
    """Prepare dense CV text for retrieval.

    CVs are compact, sectioned documents. The transformer keeps paragraphs and
    bullets together where possible, then falls back to smaller separators only
    when needed. This mirrors robust ETL design: clean the source, keep source
    lineage in metadata, and preserve business meaning during normalization.
    """

    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=[
                "\n\n",
                "\n- ",
                "\n• ",
                "\n– ",
                "\n* ",
                "\n",
                ". ",
                "; ",
                ", ",
                " ",
                "",
            ],
            add_start_index=True,
        )

    def transform(self, documents: list[Document]) -> list[Document]:
        cleaned_documents = [self._clean_document(document) for document in documents]
        chunks = self.splitter.split_documents(cleaned_documents)

        for index, chunk in enumerate(chunks):
            chunk.metadata["section"] = self._infer_section(chunk.page_content)
            chunk.metadata.update(
                {
                    "chunk_id": index,
                    "chunk_size": self.config.chunk_size,
                    "chunk_overlap": self.config.chunk_overlap,
                }
            )

        return chunks

    @staticmethod
    def _clean_document(document: Document) -> Document:
        """Normalize whitespace while preserving line-based CV structure."""

        text = document.page_content
        text = text.replace("\x00", " ")
        text = text.replace("–", "-").replace("—", "-")
        text = text.replace("•", "-")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = "\n".join(line.strip() for line in text.splitlines())

        return Document(
            page_content=text.strip(),
            metadata=dict(document.metadata),
        )

    @staticmethod
    def _infer_section(text: str) -> str:
        lowered = text.lower()
        section_markers = {
            "summary": ["summary", "profile"],
            "skills": ["technical skills", "skills"],
            "experience": ["experience", "work experience"],
            "projects": ["selected projects", "projects"],
            "research": ["research", "publications"],
            "education": ["education"],
            "certifications": ["certifications", "credentials"],
            "portfolio": ["selected systems", "capabilities", "proof"],
        }

        for section, markers in section_markers.items():
            if any(marker in lowered for marker in markers):
                return section

        return "general"
