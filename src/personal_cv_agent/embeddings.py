"""Embedding model factory."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from personal_cv_agent.config import IngestionConfig


def build_embedding_model(config: IngestionConfig) -> Embeddings:
    """Build the configured embedding model.

    OpenAI's text-embedding-3-small is the default because it gives strong
    retrieval quality at low cost and stores compact vectors for local Chroma.
    For offline or privacy-sensitive experimentation, set
    CV_AGENT_EMBEDDING_PROVIDER=huggingface to use BAAI/bge-small-en-v1.5. That
    model is a practical open-source alternative: fast on CPU, good semantic
    retrieval quality, and easy to run locally without sending CV data to an API.
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

    raise ValueError(
        "Unsupported embedding provider "
        f"{config.embedding_provider!r}. Use 'openai' or 'huggingface'."
    )
