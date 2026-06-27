"""CLI entry point for ingesting a PDF CV into the local vector database."""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from personal_cv_agent import CVIngestionPipeline, IngestionConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a PDF CV into the Personalized CV Agent vector DB.",
    )
    parser.add_argument(
        "pdf_paths",
        nargs="*",
        type=Path,
        help="Path(s) to baseline CV PDF files.",
    )
    parser.add_argument(
        "--portfolio-path",
        action="append",
        type=Path,
        default=[],
        help="Portfolio folder or file to ingest. Can be passed multiple times.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["openai", "huggingface", "gemini"],
        default=None,
        help="Override the embedding provider from .env.",
    )
    parser.add_argument(
        "--vector-db-dir",
        type=Path,
        default=None,
        help="Override the local Chroma persistence directory.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    config = IngestionConfig.from_env()

    if args.embedding_provider:
        config = IngestionConfig(
            vector_db_dir=config.vector_db_dir,
            collection_name=config.collection_name,
            embedding_provider=args.embedding_provider,
            openai_embedding_model=config.openai_embedding_model,
            huggingface_embedding_model=config.huggingface_embedding_model,
            google_embedding_model=config.google_embedding_model,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            retrieval_k=config.retrieval_k,
            retrieval_fetch_k=config.retrieval_fetch_k,
            retrieval_lambda_mult=config.retrieval_lambda_mult,
        )

    if args.vector_db_dir:
        config = IngestionConfig(
            vector_db_dir=args.vector_db_dir,
            collection_name=config.collection_name,
            embedding_provider=config.embedding_provider,
            openai_embedding_model=config.openai_embedding_model,
            huggingface_embedding_model=config.huggingface_embedding_model,
            google_embedding_model=config.google_embedding_model,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            retrieval_k=config.retrieval_k,
            retrieval_fetch_k=config.retrieval_fetch_k,
            retrieval_lambda_mult=config.retrieval_lambda_mult,
        )

    if not args.pdf_paths and not args.portfolio_path:
        raise SystemExit("Provide at least one PDF path or --portfolio-path.")

    result = CVIngestionPipeline(config).ingest_sources(
        pdf_paths=args.pdf_paths,
        portfolio_paths=args.portfolio_path,
    )

    print("CV ingestion complete")
    print(f"Source: {result.source_path}")
    print(f"Pages loaded: {result.pages_loaded}")
    print(f"Chunks created: {result.chunks_created}")
    print(f"Vector DB: {result.vector_db_dir}")
    print(f"Collection: {result.collection_name}")


if __name__ == "__main__":
    main()
