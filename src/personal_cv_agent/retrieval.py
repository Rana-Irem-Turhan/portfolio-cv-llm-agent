"""Job-aware evidence retrieval from the existing Chroma knowledge base."""

from __future__ import annotations

from pathlib import Path

from personal_cv_agent.config import IngestionConfig
from personal_cv_agent.schemas import EvidenceItem, EvidencePack, JobAnalysis, RetrievalQuerySet


RELEVANCE_QUERIES = {
    "summary": "summary_query",
    "skills": "skills_query",
    "experience": "experience_query",
    "projects": "projects_query",
    "certifications": "certifications_query",
}


def build_retrieval_queries(job: JobAnalysis) -> RetrievalQuerySet:
    """Create section-specific retrieval queries from job requirements."""

    skills = " ".join([*job.must_have_skills, *job.nice_to_have_skills])
    responsibilities = " ".join(job.responsibilities[:5])
    keywords = " ".join(job.keywords)

    return RetrievalQuerySet(
        summary_query=f"{job.role_title} {job.role_family} {skills} {keywords}".strip(),
        skills_query=f"technical skills tools {skills} {keywords}".strip(),
        experience_query=f"work experience responsibilities {job.role_title} {responsibilities} {skills}".strip(),
        projects_query=f"projects outcomes portfolio {job.role_family} {skills} {keywords}".strip(),
        certifications_query=f"certifications education credentials languages SAP cloud research {skills} {keywords}".strip(),
    )


class EvidenceRetriever:
    """Retrieve evidence chunks from the Chroma knowledge base."""

    def __init__(self, config: IngestionConfig) -> None:
        self.config = config

    def retrieve(self, job: JobAnalysis) -> EvidencePack:
        vector_db_dir = self.config.vector_db_dir.expanduser()
        if not self._has_chroma_data(vector_db_dir):
            raise RuntimeError(
                f"No ChromaDB knowledge base found at {vector_db_dir}. "
                "Run scripts/ingest_cv.py first."
            )

        queries = build_retrieval_queries(job)
        retriever = self._build_retriever()
        evidence_items: list[EvidenceItem] = []
        seen = set()

        for area, query_attr in RELEVANCE_QUERIES.items():
            query = getattr(queries, query_attr)
            documents = self._invoke_retriever(retriever, query)

            for document in documents:
                key = self._dedupe_key(document)
                if key in seen:
                    continue
                seen.add(key)
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"E{len(evidence_items) + 1}",
                        content=self._clean_content(document.page_content),
                        source_type=str(document.metadata.get("source_type", "unknown")),
                        source_file=str(document.metadata.get("source_file", "unknown")),
                        section=str(document.metadata.get("section", "general")),
                        relevance_area=area,  # type: ignore[arg-type]
                    )
                )

                if len(evidence_items) >= 20:
                    break

            if len(evidence_items) >= 20:
                break

        if not evidence_items:
            raise RuntimeError(
                "No relevant evidence was retrieved. Check that ingestion completed "
                "and the job posting contains enough detail."
            )

        return EvidencePack(job=job, queries=queries, items=evidence_items)

    def _build_retriever(self):
        try:
            from personal_cv_agent.vector_store import ChromaVectorStore

            return ChromaVectorStore(self.config).as_retriever()
        except Exception as exc:  # pragma: no cover - depends on local embedding backend
            message = str(exc)
            if self.config.embedding_provider == "openai":
                message += (
                    "\nOpenAI embeddings require OPENAI_API_KEY. Add it to .env "
                    "or use --embedding-provider huggingface."
                )
            raise RuntimeError(message) from exc

    def _invoke_retriever(self, retriever, query: str) -> list:
        try:
            if hasattr(retriever, "invoke"):
                return list(retriever.invoke(query))
            return list(retriever.get_relevant_documents(query))
        except Exception as exc:  # pragma: no cover - depends on Chroma runtime
            raise RuntimeError(f"Evidence retrieval failed for query {query!r}: {exc}") from exc

    def _has_chroma_data(self, vector_db_dir: Path) -> bool:
        if not vector_db_dir.exists():
            return False
        return any(vector_db_dir.iterdir())

    def _dedupe_key(self, document) -> tuple[str, str, str]:
        metadata = document.metadata
        return (
            str(metadata.get("source_file", "unknown")),
            str(metadata.get("section", "general")),
            document.page_content[:160],
        )

    def _clean_content(self, content: str) -> str:
        return " ".join(content.split())
