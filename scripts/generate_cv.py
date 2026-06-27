"""CLI entry point for generating a job-aware Markdown CV."""

from __future__ import annotations

import argparse
from pathlib import Path

from personal_cv_agent.config import IngestionConfig
from personal_cv_agent.generator import MarkdownCVGenerator
from personal_cv_agent.job_analysis import RuleBasedJobAnalyzer, load_job_posting
from personal_cv_agent.planner import CVPlanner
from personal_cv_agent.retrieval import EvidenceRetriever
from personal_cv_agent.validator import BasicCVValidator

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - only used in lean local environments
    def load_dotenv() -> bool:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an evidence-grounded Markdown CV from a job posting.",
    )
    parser.add_argument(
        "--job-posting",
        type=Path,
        required=True,
        help="Path to a local .txt job posting.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path where the generated Markdown CV should be written.",
    )
    parser.add_argument(
        "--embedding-provider",
        choices=["openai", "huggingface"],
        default=None,
        help="Override the embedding provider from .env.",
    )
    parser.add_argument(
        "--vector-db-dir",
        type=Path,
        default=None,
        help="Override the local Chroma persistence directory.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail without writing output if validation reports errors.",
    )
    parser.add_argument(
        "--include-evidence-ids",
        action="store_true",
        help="Append evidence references to the Markdown output for debugging.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> IngestionConfig:
    config = IngestionConfig.from_env()

    if args.embedding_provider:
        config = IngestionConfig(
            vector_db_dir=config.vector_db_dir,
            collection_name=config.collection_name,
            embedding_provider=args.embedding_provider,
            openai_embedding_model=config.openai_embedding_model,
            huggingface_embedding_model=config.huggingface_embedding_model,
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
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            retrieval_k=config.retrieval_k,
            retrieval_fetch_k=config.retrieval_fetch_k,
            retrieval_lambda_mult=config.retrieval_lambda_mult,
        )

    return config


def main() -> None:
    load_dotenv()
    args = parse_args()
    config = build_config(args)

    try:
        raw_job = load_job_posting(args.job_posting)
        job = RuleBasedJobAnalyzer().analyze(raw_job)
        evidence_pack = EvidenceRetriever(config).retrieve(job)
        plan = CVPlanner().create_plan(evidence_pack)
        markdown_cv = MarkdownCVGenerator(
            include_evidence_ids=args.include_evidence_ids,
        ).generate(plan, evidence_pack)
        report = BasicCVValidator().validate(markdown_cv, evidence_pack)

        if args.strict and not report.passed:
            print_validation_report(report)
            raise SystemExit("Validation failed in strict mode. Output was not written.")

        output_path = args.output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_cv.markdown, encoding="utf-8")

        print("Markdown CV generation complete")
        print(f"Role: {job.role_title}")
        print(f"Role family: {job.role_family}")
        print(f"Evidence items retrieved: {len(evidence_pack.items)}")
        print(f"Output: {output_path}")
        print_validation_report(report)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc


def print_validation_report(report) -> None:
    print("Validation report")
    print(f"Passed: {report.passed}")
    print(f"Word count: {report.word_count}")
    print(f"Estimated pages: {report.estimated_pages}")
    if not report.issues:
        print("Issues: none")
        return
    print("Issues:")
    for issue in report.issues:
        location = f" [{issue.section}]" if issue.section else ""
        print(f"- {issue.severity.upper()}{location}: {issue.message}")


if __name__ == "__main__":
    main()
