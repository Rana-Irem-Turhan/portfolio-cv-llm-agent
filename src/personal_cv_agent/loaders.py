"""Document loaders for the ingestion layer."""

from __future__ import annotations

from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


class CVPdfLoader:
    """Extract raw page documents from a PDF CV.

    This class is intentionally narrow: it owns PDF extraction only. Additional
    loaders for portfolio websites, project pages, blogs, and technical articles
    can later implement the same `load` shape and feed the shared transformer.
    """

    def load(self, pdf_path: Path) -> list[Document]:
        pdf_path = pdf_path.expanduser().resolve()

        if not pdf_path.exists():
            raise FileNotFoundError(f"CV PDF not found: {pdf_path}")

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a .pdf file, got: {pdf_path}")

        loader = PyPDFLoader(str(pdf_path))
        documents = loader.load()

        for document in documents:
            document.metadata.update(
                {
                    "source_type": "cv_pdf",
                    "source_file": pdf_path.name,
                    "source_path": str(pdf_path),
                }
            )

        return documents
