"""Transformation layer: cleaning and semantic chunking."""

from __future__ import annotations

import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from personal_cv_agent.config import IngestionConfig


class CVDenseTextTransformer:
    """Prepare dense CV text for retrieval."""

    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=[
                "\n\n",
                "\n- ",
                "\n\u2022 ",
                "\n\u2013 ",
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

        text = document.page_content.replace("\x00", " ")
        text = CVDenseTextTransformer._normalize_text_artifacts(text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = "\n".join(line.strip() for line in text.splitlines())

        return Document(
            page_content=text.strip(),
            metadata=dict(document.metadata),
        )

    @staticmethod
    def _normalize_text_artifacts(text: str) -> str:
        replacements = {
            "\u2013": "-",
            "\u2014": "-",
            "\u2022": "-",
            "\u201c": '"',
            "\u201d": '"',
            "\u2018": "'",
            "\u2019": "'",
            "\u00b7": "-",
            "\u00c2": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = re.sub(r"[\u00e2\u00f0][^\s]{0,12}", " ", text)
        return text

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
