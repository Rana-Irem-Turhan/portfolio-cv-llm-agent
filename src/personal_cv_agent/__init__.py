"""Personalized CV Agent ingestion package."""

from personal_cv_agent.config import IngestionConfig
from personal_cv_agent.pipeline import CVIngestionPipeline

__all__ = ["CVIngestionPipeline", "IngestionConfig"]
