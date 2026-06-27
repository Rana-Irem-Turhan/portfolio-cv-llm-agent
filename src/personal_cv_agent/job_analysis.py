"""Rule-based job posting loading and analysis."""

from __future__ import annotations

import re
from pathlib import Path

from personal_cv_agent.schemas import JobAnalysis, RoleFamily


SKILL_VOCABULARY = [
    "SQL",
    "Python",
    "PostgreSQL",
    "ETL",
    "ELT",
    "Data Warehousing",
    "Data Warehouse",
    "Data Modeling",
    "Data Quality",
    "Data Validation",
    "Power BI",
    "AWS",
    "S3",
    "EC2",
    "RDS",
    "Redshift",
    "Athena",
    "Git",
    "GitHub",
    "Agile",
    "Scrum",
    "RAG",
    "Retrieval-Augmented Generation",
    "LLM",
    "LLMs",
    "Vector Search",
    "Embeddings",
    "FAISS",
    "Hugging Face",
    "Prompt Engineering",
    "Scikit-learn",
    "TensorFlow",
    "Keras",
    "LightGBM",
    "XGBoost",
    "OpenCV",
    "Computer Vision",
    "Machine Learning",
    "Deep Learning",
    "Healthcare AI",
    "Clinical",
    "SAP",
    "S/4HANA",
    "Analytics",
    "Business Intelligence",
]

RESPONSIBILITY_VERBS = [
    "analyze",
    "build",
    "collaborate",
    "communicate",
    "create",
    "design",
    "develop",
    "document",
    "implement",
    "improve",
    "maintain",
    "model",
    "optimize",
    "support",
    "validate",
    "work",
]


def load_job_posting(path: Path) -> str:
    """Read a local .txt job posting and return normalized text."""

    job_path = path.expanduser().resolve()

    if not job_path.exists():
        raise FileNotFoundError(f"Job posting not found: {job_path}")

    if job_path.suffix.lower() != ".txt":
        raise ValueError(f"Expected a .txt job posting, got: {job_path}")

    text = job_path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.splitlines()).strip()

    if not text:
        raise ValueError(f"Job posting is empty: {job_path}")

    return text


class RuleBasedJobAnalyzer:
    """Conservative job analyzer that does not require an LLM."""

    def analyze(self, raw_text: str) -> JobAnalysis:
        text = raw_text.strip()
        if not text:
            raise ValueError("Job posting text is empty.")

        role_title = self._infer_role_title(text)
        must_have, nice_to_have = self._extract_skills_by_section(text)
        responsibilities = self._extract_responsibilities(text)
        keywords = self._dedupe(
            [role_title, *must_have, *nice_to_have, *self._extract_domain_keywords(text)]
        )

        return JobAnalysis(
            role_title=role_title,
            company=self._extract_label(text, "company"),
            location=self._extract_label(text, "location"),
            seniority=self._infer_seniority(text),
            role_family=self._infer_role_family(text, role_title),
            must_have_skills=must_have,
            nice_to_have_skills=nice_to_have,
            responsibilities=responsibilities,
            keywords=keywords,
            raw_text=text,
        )

    def _infer_role_title(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip(" -:\t")
            if not stripped:
                continue
            if len(stripped) <= 80 and not stripped.lower().startswith(
                ("we are", "about", "responsibilities", "required", "nice")
            ):
                return stripped
        return "Target Role"

    def _extract_skills_by_section(self, text: str) -> tuple[list[str], list[str]]:
        required_block = self._section_text(
            text,
            starts=("required", "requirements", "must have", "qualifications"),
            stops=("nice", "preferred", "responsibilities", "about", "benefits"),
        )
        nice_block = self._section_text(
            text,
            starts=("nice", "preferred", "bonus", "nice to have"),
            stops=("responsibilities", "about", "benefits"),
        )

        required = self._extract_skills(required_block or text)
        nice = [skill for skill in self._extract_skills(nice_block) if skill not in required]

        return required, nice

    def _extract_skills(self, text: str) -> list[str]:
        found: list[str] = []
        lowered = text.lower()

        for skill in SKILL_VOCABULARY:
            if skill.lower() in lowered:
                found.append(skill)

        return self._dedupe(found)

    def _extract_responsibilities(self, text: str) -> list[str]:
        responsibilities: list[str] = []
        for line in text.splitlines():
            cleaned = line.strip(" -•\t")
            if len(cleaned) < 20:
                continue
            lowered = cleaned.lower()
            if any(re.search(rf"\b{verb}\w*\b", lowered) for verb in RESPONSIBILITY_VERBS):
                responsibilities.append(cleaned)
            if len(responsibilities) >= 8:
                break
        return self._dedupe(responsibilities)

    def _infer_role_family(self, text: str, role_title: str) -> RoleFamily:
        haystack = f"{role_title}\n{text}".lower()

        if any(term in haystack for term in ("clinical", "healthcare", "genomic", "biomedical")):
            return "healthcare_ai"
        if any(term in haystack for term in ("rag", "llm", "ai engineer", "ai agent", "prompt")):
            return "ai_engineer"
        if any(term in haystack for term in ("data engineer", "etl", "warehouse", "pipeline")):
            return "data_engineer"
        if any(term in haystack for term in ("machine learning", "ml engineer", "computer vision")):
            return "ml_engineer"
        if any(term in haystack for term in ("data analyst", "analytics", "business intelligence", "power bi")):
            return "data_analyst"
        if any(term in haystack for term in ("consultant", "sap", "stakeholder")):
            return "consulting"
        if any(term in haystack for term in ("software engineer", "backend", "frontend")):
            return "software_engineering"
        if any(term in haystack for term in ("product", "mvp", "user flow")):
            return "product_ai"
        return "unknown"

    def _infer_seniority(self, text: str) -> str | None:
        lowered = text.lower()
        if any(term in lowered for term in ("intern", "internship")):
            return "intern"
        if any(term in lowered for term in ("junior", "entry level", "early career")):
            return "junior"
        if "senior" in lowered:
            return "senior"
        return None

    def _extract_domain_keywords(self, text: str) -> list[str]:
        keywords = []
        for phrase in (
            "analytics",
            "business intelligence",
            "data platform",
            "reporting",
            "healthcare",
            "computer vision",
            "geospatial",
            "enterprise",
            "cloud",
        ):
            if phrase in text.lower():
                keywords.append(phrase)
        return keywords

    def _section_text(
        self,
        text: str,
        starts: tuple[str, ...],
        stops: tuple[str, ...],
    ) -> str:
        lines = text.splitlines()
        collecting = False
        collected: list[str] = []

        for line in lines:
            lowered = line.strip().lower().rstrip(":")
            if any(lowered.startswith(start) for start in starts):
                collecting = True
                continue
            if collecting and any(lowered.startswith(stop) for stop in stops):
                break
            if collecting:
                collected.append(line)

        return "\n".join(collected).strip()

    def _extract_label(self, text: str, label: str) -> str | None:
        match = re.search(rf"^{label}\s*:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            return None
        return match.group(1).strip()

    def _dedupe(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            normalized = value.strip()
            key = normalized.lower()
            if normalized and key not in seen:
                seen.add(key)
                result.append(normalized)
        return result
