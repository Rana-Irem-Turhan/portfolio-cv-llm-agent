"""Personalized CV Agent package."""

from personal_cv_agent.config import IngestionConfig

__all__ = ["CVIngestionPipeline", "IngestionConfig"]


def __getattr__(name: str):
    """Load heavier ingestion dependencies only when they are requested."""

    if name == "CVIngestionPipeline":
        from personal_cv_agent.pipeline import CVIngestionPipeline

        return CVIngestionPipeline

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
