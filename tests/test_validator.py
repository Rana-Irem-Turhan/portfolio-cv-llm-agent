import unittest

from personal_cv_agent.schemas import EvidenceItem, EvidencePack, JobAnalysis, MarkdownCV, RetrievalQuerySet
from personal_cv_agent.validator import BasicCVValidator


def _evidence_pack(content: str) -> EvidencePack:
    job = JobAnalysis(
        role_title="Data Engineer",
        role_family="data_engineer",
        must_have_skills=["SQL"],
        nice_to_have_skills=[],
        responsibilities=[],
        keywords=["SQL"],
        raw_text="Data Engineer SQL",
    )
    queries = RetrievalQuerySet(
        summary_query="Data Engineer",
        skills_query="SQL",
        experience_query="ETL",
        projects_query="projects",
        certifications_query="certifications",
    )
    return EvidencePack(
        job=job,
        queries=queries,
        items=[
            EvidenceItem(
                evidence_id="E1",
                content=content,
                source_type="cv_pdf",
                source_file="cv.pdf",
                section="experience",
                relevance_area="experience",
            )
        ],
    )


class ValidatorTests(unittest.TestCase):
    def test_validator_detects_missing_sections(self):
        cv = MarkdownCV(markdown="# Rana Irem Turhan\n\nSome text only.", evidence_ids=["E1"])
        report = BasicCVValidator().validate(cv, _evidence_pack("Worked on ETL validation using SQL."))

        self.assertFalse(report.passed)
        self.assertTrue(any("Missing required section" in issue.message for issue in report.issues))

    def test_validator_warns_on_unsupported_number(self):
        markdown = """# Rana Irem Turhan

## Summary
Evidence-grounded data engineer.

## Technical Skills
- SQL

## Experience
- Improved ETL performance by 40%.

## Selected Projects
- Worked on ETL validation.
"""
        cv = MarkdownCV(markdown=markdown, evidence_ids=["E1"])
        report = BasicCVValidator().validate(cv, _evidence_pack("Worked on ETL validation using SQL and Python."))

        self.assertTrue(any("40%" in issue.message for issue in report.issues))


if __name__ == "__main__":
    unittest.main()
