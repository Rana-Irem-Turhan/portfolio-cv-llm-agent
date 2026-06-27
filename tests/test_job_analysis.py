from pathlib import Path
import tempfile
import unittest

from personal_cv_agent.job_analysis import RuleBasedJobAnalyzer, load_job_posting


class JobAnalysisTests(unittest.TestCase):
    def test_job_analysis_detects_data_engineer(self):
        job = RuleBasedJobAnalyzer().analyze(
            "Data Engineer\nWe need SQL, Python, AWS, ETL pipelines, data warehouse modeling, and data quality validation."
        )

        self.assertEqual(job.role_family, "data_engineer")
        self.assertIn("SQL", job.must_have_skills)
        self.assertIn("Python", job.must_have_skills)
        self.assertIn("AWS", job.must_have_skills)
        self.assertIn("ETL", job.must_have_skills)

    def test_job_analysis_detects_ai_engineer(self):
        job = RuleBasedJobAnalyzer().analyze(
            "AI Engineer\nBuild RAG applications using vector search, embeddings, LLMs, prompt engineering, and Python."
        )

        self.assertEqual(job.role_family, "ai_engineer")
        self.assertIn("RAG", job.must_have_skills)
        self.assertIn("Vector Search", job.must_have_skills)
        self.assertIn("Python", job.must_have_skills)

    def test_empty_job_posting_fails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.txt"
            path.write_text("", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_job_posting(path)


if __name__ == "__main__":
    unittest.main()
