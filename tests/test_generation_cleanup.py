import unittest

from personal_cv_agent.generator import MarkdownCVGenerator
from personal_cv_agent.portfolio_loader import PortfolioSourceLoader
from personal_cv_agent.schemas import CVPlan, EvidenceItem, EvidencePack, JobAnalysis, RetrievalQuerySet


class GenerationCleanupTests(unittest.TestCase):
    def test_generator_filters_code_like_evidence(self):
        pack = self._pack(
            [
                'const experiences: Experience[] = [ { role: "Data Analytics Engineering Intern" } ]',
                "Performed source-to-target reconciliation and data quality validation using SQL and Python.",
            ]
        )
        plan = CVPlan(
            target_title="Data Engineer Intern",
            summary_angle="data engineering and SQL validation",
            skill_groups=["SQL", "Python"],
        )

        markdown = MarkdownCVGenerator().generate(plan, pack).markdown

        self.assertNotIn("const experiences", markdown)
        self.assertNotIn("Experience[]", markdown)
        self.assertIn("source-to-target reconciliation", markdown)

    def test_generator_professionalizes_messy_evidence(self):
        pack = self._pack(
            [
                "Computer Vision & Geospatial AI:OpenCV, ResNet, VGG, EfficientNet, Satellite Imagery Analysis",
                "Expected to work on project-based AI development involving prompt engineering.",
            ]
        )
        plan = CVPlan(
            target_title="ML Engineer Intern",
            summary_angle="machine learning and computer vision",
            skill_groups=["OpenCV"],
        )

        markdown = MarkdownCVGenerator().generate(plan, pack).markdown

        self.assertIn("Supported geospatial computer vision workflows", markdown)
        self.assertNotIn("Expected to work", markdown)

    def test_portfolio_loader_cleans_typescript_source_syntax(self):
        raw = 'export const experiences: Experience[] = [{ id: "epam", role: "Data Analytics Engineering Intern", company: "EPAM Systems" }];'

        cleaned = PortfolioSourceLoader._clean_source_text(raw, ".ts")

        self.assertNotIn("export const", cleaned)
        self.assertNotIn("Experience[]", cleaned)
        self.assertIn("Data Analytics Engineering Intern", cleaned)
        self.assertIn("EPAM Systems", cleaned)

    def _pack(self, contents: list[str]) -> EvidencePack:
        job = JobAnalysis(
            role_title="Data Engineer Intern",
            role_family="data_engineer",
            must_have_skills=["SQL", "Python"],
            nice_to_have_skills=[],
            responsibilities=[],
            keywords=["SQL", "Python", "data quality"],
            raw_text="Data Engineer Intern SQL Python",
        )
        queries = RetrievalQuerySet(
            summary_query="Data Engineer",
            skills_query="SQL Python",
            experience_query="data quality",
            projects_query="projects",
            certifications_query="certifications",
        )
        return EvidencePack(
            job=job,
            queries=queries,
            items=[
                EvidenceItem(
                    evidence_id=f"E{index + 1}",
                    content=content,
                    source_type="portfolio",
                    source_file="fixture",
                    section="experience",
                    relevance_area="experience",
                )
                for index, content in enumerate(contents)
            ],
        )


if __name__ == "__main__":
    unittest.main()
