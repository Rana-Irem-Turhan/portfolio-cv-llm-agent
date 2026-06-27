"""Conservative CV planning from retrieved evidence."""

from __future__ import annotations

from personal_cv_agent.schemas import CVPlan, EvidencePack


ROLE_SUMMARY_ANGLES = {
    "data_engineer": "data engineering, SQL, ETL validation, data warehousing, data quality, and analytics workflows",
    "data_analyst": "analytics, SQL, reporting, BI workflows, data quality, and stakeholder-facing insights",
    "ai_engineer": "RAG systems, LLM applications, vector search, prompt engineering, and applied AI delivery",
    "ml_engineer": "machine learning, model evaluation, Python workflows, computer vision, and applied experimentation",
    "healthcare_ai": "applied AI, healthcare-oriented model reliability, transparency, and responsible system design",
    "product_ai": "AI product discovery, MVP scoping, user workflows, and responsible applied AI architecture",
    "consulting": "enterprise analytics, SAP context, stakeholder communication, and business process translation",
    "software_engineering": "Python, SQL, data-intensive tooling, reusable logic, and system reliability",
    "unknown": "role-relevant technical evidence, applied AI, data engineering, and analytics delivery",
}


class CVPlanner:
    """Create a compact plan before Markdown generation."""

    def create_plan(self, evidence_pack: EvidencePack) -> CVPlan:
        job = evidence_pack.job
        evidence_text = " ".join(item.content for item in evidence_pack.items).lower()
        supported_skills = [
            skill
            for skill in [*job.must_have_skills, *job.nice_to_have_skills]
            if skill.lower() in evidence_text
        ]

        return CVPlan(
            target_title=job.role_title,
            summary_angle=ROLE_SUMMARY_ANGLES.get(job.role_family, ROLE_SUMMARY_ANGLES["unknown"]),
            skill_groups=supported_skills[:14],
            experience_focus=self._focus_ids(evidence_pack, "experience"),
            project_focus=self._focus_ids(evidence_pack, "projects"),
            certification_focus=self._focus_ids(evidence_pack, "certifications"),
            omitted_or_deemphasized=self._omissions(job.role_family),
        )

    def _focus_ids(self, evidence_pack: EvidencePack, relevance_area: str) -> list[str]:
        ids = [
            item.evidence_id
            for item in evidence_pack.items
            if item.relevance_area == relevance_area or item.section == relevance_area
        ]
        return ids[:6]

    def _omissions(self, role_family: str) -> list[str]:
        if role_family == "data_engineer":
            return ["Keep AI research concise unless it supports data platform or automation work."]
        if role_family == "ai_engineer":
            return ["Keep BI/dashboard details concise unless they demonstrate production data grounding."]
        if role_family == "ml_engineer":
            return ["Keep SAP and consulting details concise unless requested by the job posting."]
        return ["Omit weakly supported or low-relevance claims to preserve a concise two-page CV draft."]
