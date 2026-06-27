import unittest

from personal_cv_agent.retrieval import build_retrieval_queries
from personal_cv_agent.schemas import JobAnalysis


class RetrievalTests(unittest.TestCase):
    def test_retrieval_queries_include_job_terms(self):
        job = JobAnalysis(
            role_title="Data Engineer",
            role_family="data_engineer",
            must_have_skills=["SQL", "AWS"],
            nice_to_have_skills=[],
            responsibilities=["Build ETL pipelines."],
            keywords=["data platform"],
            raw_text="Data Engineer with SQL and AWS.",
        )

        queries = build_retrieval_queries(job)

        self.assertIn("Data Engineer", queries.summary_query)
        self.assertIn("SQL", queries.skills_query)
        self.assertIn("AWS", queries.skills_query)
        self.assertIn("Build ETL pipelines", queries.experience_query)


if __name__ == "__main__":
    unittest.main()
