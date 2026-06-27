"""ATS-friendly Markdown CV generation from retrieved evidence."""

from __future__ import annotations

import re

from personal_cv_agent.schemas import CVPlan, EvidenceItem, EvidencePack, MarkdownCV


class MarkdownCVGenerator:
    """Generate conservative Markdown CV drafts from evidence."""

    def __init__(self, include_evidence_ids: bool = False) -> None:
        self.include_evidence_ids = include_evidence_ids

    def generate(self, plan: CVPlan, evidence_pack: EvidencePack) -> MarkdownCV:
        evidence_text = "\n".join(item.content for item in evidence_pack.items)
        name = self._extract_name(evidence_text)
        contact = self._extract_contact_line(evidence_text)
        evidence_ids = [item.evidence_id for item in evidence_pack.items]

        sections = [
            f"# {name}",
            "",
            contact,
            "",
            "## Summary",
            "",
            self._summary(plan, evidence_pack),
            "",
            "## Technical Skills",
            "",
            *self._skills(plan, evidence_pack),
            "",
            "## Experience",
            "",
            *self._bullets_for_area(evidence_pack, "experience", fallback_area="summary", max_bullets=6),
            "",
            "## Selected Projects",
            "",
            *self._bullets_for_area(evidence_pack, "projects", fallback_area="experience", max_bullets=5),
            "",
            "## Education",
            "",
            *self._education(evidence_pack),
            "",
            "## Certifications",
            "",
            *self._certifications(evidence_pack),
        ]

        if self.include_evidence_ids:
            sections.extend(
                [
                    "",
                    "## Evidence References",
                    "",
                    *[f"- {item.evidence_id}: {item.source_file} ({item.section})" for item in evidence_pack.items],
                ]
            )

        markdown = "\n".join(line for line in sections if line is not None).strip() + "\n"
        return MarkdownCV(markdown=markdown, evidence_ids=evidence_ids)

    def _summary(self, plan: CVPlan, evidence_pack: EvidencePack) -> str:
        supported_skills = ", ".join(plan.skill_groups[:8])
        if supported_skills:
            return (
                f"Evidence-grounded candidate for {plan.target_title} roles, with retrieved background aligned to "
                f"{plan.summary_angle}. Relevant supported skills include {supported_skills}."
            )
        return (
            f"Evidence-grounded candidate for {plan.target_title} roles, with retrieved background aligned to "
            f"{plan.summary_angle}. Generated conservatively from the available knowledge base."
        )

    def _skills(self, plan: CVPlan, evidence_pack: EvidencePack) -> list[str]:
        if plan.skill_groups:
            return [f"- Role-relevant skills: {', '.join(plan.skill_groups[:14])}"]

        skills = self._terms_from_evidence(evidence_pack)
        if skills:
            return [f"- Evidence-supported skills: {', '.join(skills[:14])}"]

        return ["- Evidence-supported skills: See retrieved CV and portfolio evidence."]

    def _education(self, evidence_pack: EvidencePack) -> list[str]:
        bullets = self._sentences_matching(evidence_pack.items, ("education", "university", "bachelor", "degree"))
        return self._format_bullets(bullets[:2]) or ["- Education details available in retrieved CV evidence."]

    def _certifications(self, evidence_pack: EvidencePack) -> list[str]:
        bullets = self._sentences_matching(
            evidence_pack.items,
            ("certification", "certified", "certificate", "ielts", "sap", "hackerrank"),
        )
        return self._format_bullets(bullets[:5]) or ["- Certifications available in retrieved CV evidence."]

    def _bullets_for_area(
        self,
        evidence_pack: EvidencePack,
        area: str,
        fallback_area: str,
        max_bullets: int,
    ) -> list[str]:
        items = [
            item
            for item in evidence_pack.items
            if item.relevance_area == area or item.section == area
        ]
        if not items:
            items = [item for item in evidence_pack.items if item.relevance_area == fallback_area]

        job_terms = tuple(term.lower() for term in evidence_pack.job.keywords + evidence_pack.job.must_have_skills)
        bullets = self._sentences_matching(items, job_terms)
        if not bullets:
            bullets = [self._shorten(item.content) for item in items]

        return self._format_bullets(bullets[:max_bullets]) or ["- Relevant evidence was retrieved but needs manual review."]

    def _sentences_matching(self, items: list[EvidenceItem], terms: tuple[str, ...]) -> list[str]:
        bullets: list[str] = []
        for item in items:
            for sentence in self._split_sentences(item.content):
                lowered = sentence.lower()
                if any(term and term in lowered for term in terms):
                    bullets.append(self._shorten(sentence))
                if len(bullets) >= 10:
                    return self._dedupe(bullets)
        return self._dedupe(bullets)

    def _split_sentences(self, text: str) -> list[str]:
        normalized = text.replace(" - ", ". ").replace(" – ", ". ")
        parts = re.split(r"(?<=[.!?])\s+|\s+-\s+", normalized)
        return [part.strip(" -•") for part in parts if len(part.strip()) >= 35]

    def _format_bullets(self, bullets: list[str]) -> list[str]:
        return [f"- {bullet}" for bullet in self._dedupe(bullets) if bullet]

    def _shorten(self, text: str, limit: int = 220) -> str:
        cleaned = " ".join(text.split()).strip(" -•")
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 3].rsplit(" ", 1)[0] + "..."

    def _extract_name(self, evidence_text: str) -> str:
        match = re.search(r"\bRana\s+Irem\s+Turhan\b", evidence_text, flags=re.IGNORECASE)
        if match:
            return "Rana Irem Turhan"
        return "Candidate"

    def _extract_contact_line(self, evidence_text: str) -> str:
        email = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", evidence_text)
        links = []
        for label in ("LinkedIn", "GitHub", "Portfolio"):
            if label.lower() in evidence_text.lower():
                links.append(label)

        parts = ["Istanbul, Turkey"]
        if email:
            parts.append(email.group(0))
        parts.extend(links)
        return " | ".join(self._dedupe(parts))

    def _terms_from_evidence(self, evidence_pack: EvidencePack) -> list[str]:
        evidence_text = " ".join(item.content for item in evidence_pack.items).lower()
        return [
            skill
            for skill in [*evidence_pack.job.must_have_skills, *evidence_pack.job.nice_to_have_skills]
            if skill.lower() in evidence_text
        ]

    def _dedupe(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            key = value.lower().strip()
            if key and key not in seen:
                seen.add(key)
                result.append(value)
        return result
