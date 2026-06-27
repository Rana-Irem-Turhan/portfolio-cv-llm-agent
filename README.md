# Portfolio CV LLM Agent

RAG-based personalized CV agent that ingests baseline CV PDFs and portfolio source files into a local ChromaDB knowledge base. The goal is to generate tailored, professional CVs from job postings while preserving verified career facts, portfolio evidence, and role-specific relevance.

## What It Does

- Loads PDF CVs with LangChain's PDF tooling.
- Loads portfolio source files such as README, HTML, and structured `src/data/*.ts` files.
- Cleans dense CV and portfolio text while preserving section context.
- Chunks content for retrieval-friendly storage.
- Stores embeddings in a local Chroma collection.
- Supports OpenAI embeddings by default, with an optional Hugging Face backend.

## Project Structure

```text
src/personal_cv_agent/
  config.py            Runtime configuration and retrieval defaults
  loaders.py           PDF CV loading
  portfolio_loader.py  Portfolio source loading
  transformers.py      Cleaning, section inference, and chunking
  embeddings.py        OpenAI / Hugging Face embedding factory
  vector_store.py      ChromaDB persistence and retriever setup
  pipeline.py          End-to-end ingestion orchestration
scripts/
  ingest_cv.py         CLI ingestion entry point
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

Copy the example environment file and add your API key if using OpenAI embeddings:

```bash
copy .env.example .env
```

## Ingest CVs And Portfolio Sources

```bash
python scripts/ingest_cv.py "C:\path\to\cv.pdf" --portfolio-path "C:\path\to\portfolio"
```

Multiple CVs and portfolio paths are supported:

```bash
python scripts/ingest_cv.py "C:\path\to\cv1.pdf" "C:\path\to\cv2.pdf" --portfolio-path "C:\path\to\portfolio"
```

## Generate A Markdown CV

After ingesting CV and portfolio sources into ChromaDB, generate an evidence-grounded Markdown CV from a job posting:

```bash
python scripts/generate_cv.py --job-posting data/job_postings/example_data_engineer.txt --output output/custom_cv.md
```

Useful options:

```bash
python scripts/generate_cv.py --job-posting data/job_postings/example_data_engineer.txt --output output/custom_cv.md --include-evidence-ids
python scripts/generate_cv.py --job-posting data/job_postings/example_data_engineer.txt --output output/custom_cv.md --strict
```

If the command says no ChromaDB knowledge base was found, run `scripts/ingest_cv.py` first with your local CV and portfolio sources. Do not commit private CV PDFs, generated CVs, `.env`, or `data/chroma/` to GitHub.

## Status

This repository currently contains the ingestion and retrieval foundation plus the first job-aware Markdown CV generator. The next planned layer is stronger hallucination validation, better content planning, two-page compression, and PDF generation.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the product vision, architecture, hallucination-control strategy, and phased implementation plan.
