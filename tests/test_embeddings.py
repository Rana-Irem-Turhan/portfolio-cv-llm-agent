import os
import unittest

from personal_cv_agent.config import IngestionConfig
from personal_cv_agent.embeddings import build_embedding_model


class EmbeddingProviderTests(unittest.TestCase):
    def test_config_reads_gemini_provider_and_model_from_env(self):
        previous_provider = os.environ.get("CV_AGENT_EMBEDDING_PROVIDER")
        previous_model = os.environ.get("CV_AGENT_GOOGLE_EMBEDDING_MODEL")
        os.environ["CV_AGENT_EMBEDDING_PROVIDER"] = "gemini"
        os.environ["CV_AGENT_GOOGLE_EMBEDDING_MODEL"] = "gemini-embedding-001"
        try:
            config = IngestionConfig.from_env()
        finally:
            self._restore_env("CV_AGENT_EMBEDDING_PROVIDER", previous_provider)
            self._restore_env("CV_AGENT_GOOGLE_EMBEDDING_MODEL", previous_model)

        self.assertEqual(config.embedding_provider, "gemini")
        self.assertEqual(config.google_embedding_model, "gemini-embedding-001")

    def test_gemini_provider_requires_api_key(self):
        previous_gemini = os.environ.get("GEMINI_API_KEY")
        previous_google = os.environ.get("GOOGLE_API_KEY")
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        try:
            with self.assertRaisesRegex(ValueError, "GEMINI_API_KEY or GOOGLE_API_KEY"):
                build_embedding_model(
                    IngestionConfig(
                        embedding_provider="gemini",
                        google_embedding_model="gemini-embedding-001",
                    )
                )
        finally:
            self._restore_env("GEMINI_API_KEY", previous_gemini)
            self._restore_env("GOOGLE_API_KEY", previous_google)

    def test_unsupported_provider_lists_gemini(self):
        with self.assertRaisesRegex(ValueError, "openai.*huggingface.*gemini"):
            build_embedding_model(IngestionConfig(embedding_provider="unknown"))

    def _restore_env(self, key: str, value: str | None) -> None:
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
