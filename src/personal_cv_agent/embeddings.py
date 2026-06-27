"""Embedding model factory."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

from personal_cv_agent.config import IngestionConfig


def build_embedding_model(config: IngestionConfig) -> "Embeddings":
    """Build the configured embedding model.

    OpenAI's text-embedding-3-small is the default. For local/keyless
    experimentation, set CV_AGENT_EMBEDDING_PROVIDER=huggingface. For Gemini,
    set CV_AGENT_EMBEDDING_PROVIDER=gemini and provide GEMINI_API_KEY or
    GOOGLE_API_KEY in the local environment.
    """

    provider = config.embedding_provider.strip().lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=config.openai_embedding_model)

    if provider in {"huggingface", "hf", "open-source", "opensource"}:
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=config.huggingface_embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )

    if provider in {"gemini", "google", "google-genai", "google_genai"}:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini embeddings require GEMINI_API_KEY or GOOGLE_API_KEY. "
                "Set one in your local environment or .env file; never commit secrets."
            )

        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
        except ImportError as exc:
            raise ImportError(
                "Gemini embeddings require langchain-google-genai. "
                "Install dependencies with: pip install -r requirements.txt"
            ) from exc

        return GoogleGenerativeAIEmbeddings(
            model=config.google_embedding_model,
            google_api_key=api_key,
        )

    raise ValueError(
        "Unsupported embedding provider "
        f"{config.embedding_provider!r}. Use 'openai', 'huggingface', or 'gemini'."
    )
