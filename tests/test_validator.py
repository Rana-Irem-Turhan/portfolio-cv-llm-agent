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

        self.assertFalse(report.passed)
        self.assertTrue(any("40%" in issue.message for issue in report.issues))

    def test_validator_detects_encoding_artifacts(self):
        report = self._validate_bad_bullet("Experience", "Worked at Polar CBS MÃƒÂ¼hendislik on geospatial workflows.")

        self.assertFalse(report.passed)
        self.assertTrue(any("Encoding artifact" in issue.message for issue in report.issues))

    def test_validator_detects_raw_code_fragments(self):
        report = self._validate_bad_bullet("Experience", 'const experiences: Experience[] = [{ role: "Intern" }].')

        self.assertFalse(report.passed)
        self.assertTrue(any("Raw code" in issue.message for issue in report.issues))

    def test_validator_rejects_date_only_bullet(self):
        report = self._validate_bad_bullet("Experience", "May 2026")

        self.assertFalse(report.passed)
        self.assertTrue(any("Date-only" in issue.message for issue in report.issues))

    def test_validator_rejects_future_work_phrasing(self):
        report = self._validate_bad_bullet("Experience", "Expected to work on project-based AI development.")

        self.assertFalse(report.passed)
        self.assertTrue(any("expected-work" in issue.message.lower() for issue in report.issues))

    def test_validator_detects_education_contamination(self):
        report = self._validate_bad_bullet("Education", "Created community content on ETL pipelines and machine learning.")

        self.assertFalse(report.passed)
        self.assertTrue(any(issue.section == "Education" for issue in report.issues))

    def test_validator_detects_certification_contamination(self):
        report = self._validate_bad_bullet("Certifications", "Data warehouse architecture project with GitHub Repository links.")

        self.assertFalse(report.passed)
        self.assertTrue(any(issue.section == "Certifications" for issue in report.issues))

    def test_validator_detects_repeated_bullets(self):
        markdown = self._valid_markdown().replace(
            "- Worked on ETL validation.",
            "- Worked on ETL validation.\n- Worked on ETL validation.",
        )
        report = BasicCVValidator().validate(
            MarkdownCV(markdown=markdown, evidence_ids=["E1"]),
            _evidence_pack("Worked on ETL validation using SQL and Python."),
        )

        self.assertFalse(report.passed)
        self.assertTrue(any("Repeated bullet" in issue.message for issue in report.issues))

    def test_validator_detects_navigation_text(self):
        report = self._validate_bad_bullet("Selected Projects", "Interactive Demo GitHub Repository View Certificate.")

        self.assertFalse(report.passed)
        self.assertTrue(any("navigation" in issue.message.lower() for issue in report.issues))

    def _validate_bad_bullet(self, section: str, bullet: str):
        markdown = self._valid_markdown()
        markdown = markdown.replace(f"## {section}\n- ", f"## {section}\n- {bullet}\n- ", 1)
        return BasicCVValidator().validate(
            MarkdownCV(markdown=markdown, evidence_ids=["E1"]),
            _evidence_pack("Worked on ETL validation using SQL and Python at Riga Technical University with SAP certification."),
        )

    def _valid_markdown(self) -> str:
        return """# Rana Irem Turhan

## Summary
Evidence-grounded data engineer.

## Technical Skills
- SQL and Python for data validation workflows.

## Experience
- Worked on ETL validation.

## Selected Projects
- Built retrieval workflows using Python and SQL.

## Education
- Bachelor of Engineering Science in Computer Systems - Riga Technical University.

## Certifications
- SAP Certified Associate credential.
"""


if __name__ == "__main__":
    unittest.main()
