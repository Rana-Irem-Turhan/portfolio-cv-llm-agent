# Personalized CV Agent: Ingestion Foundation

This package ingests your PDF CVs and portfolio source files into a local Chroma vector database using LangChain. It is structured as an ETL-style foundation so later sources such as job postings, GitHub README files, blogs, project writeups, and technical articles can feed the same transformer and vector-store layers.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

For the optional open-source embedding backend:

```bash
pip install ".[open-source-embeddings]"
```

## Configure

Copy `.env.example` to `.env` and add your OpenAI key:

```bash
copy .env.example .env
```

Default embedding model:

```text
text-embedding-3-small
```

This is the recommended default for your first version because it has strong retrieval quality, low cost, and compact vector size. If you need local/private embeddings, use:

```bash
set CV_AGENT_EMBEDDING_PROVIDER=huggingface
```

The configured open-source model is `BAAI/bge-small-en-v1.5`, a practical local alternative with good semantic retrieval quality and modest CPU requirements.

## Run

```bash
python scripts/ingest_cv.py "C:\path\to\your_cv.pdf"
python scripts/ingest_cv.py "C:\path\to\cv1.pdf" "C:\path\to\cv2.pdf" --portfolio-path "C:\path\to\portfolio"
```

Override provider or vector-store directory:

```bash
python scripts/ingest_cv.py "C:\path\to\your_cv.pdf" --embedding-provider huggingface --vector-db-dir data/chroma
```

## Chunk Strategy

The dense-CV defaults are:

```text
chunk_size = 900 characters
chunk_overlap = 150 characters
```

A CV is not like a long article. It has compact factual blocks where role, date, company, stack, and measurable achievements must stay together. The 900-character chunk size usually captures one section or sub-section without mixing too many unrelated facts. The 150-character overlap preserves headers and neighboring bullets across boundaries, reducing retrieval misses when a query targets a skill but the relevant company or project name sits just above it.

This mirrors ETL/DWH thinking: preserve lineage, maintain source grain, and avoid transformations that detach facts from their business meaning.

## Project Shape

```text
src/personal_cv_agent/
  config.py         Runtime configuration and chunking defaults
  loaders.py        PDF extraction via PyPDFLoader
  portfolio_loader.py Portfolio source extraction for README, HTML, and src/data/*.ts files
  transformers.py   CV cleaning and semantic chunking
  embeddings.py     OpenAI or Hugging Face embedding factory
  vector_store.py   Chroma persistence
  pipeline.py       End-to-end orchestration
scripts/
  ingest_cv.py      CLI entry point
```

Future web ingestion modules should add new loader classes that return `list[Document]`, then reuse `CVDenseTextTransformer` and `ChromaVectorStore`.
