# Milestone 2 Blueprint: Job-Aware Markdown CV Generator

## Goal

Build the first job-aware generation layer on top of the existing ingestion and ChromaDB memory layer.

Target CLI:

```bash
python scripts/generate_cv.py --job-posting data/job_postings/job.txt --output output/custom_cv.md
```

This milestone should produce a structured, ATS-friendly Markdown CV draft from:

1. A local job posting text file.
2. The existing ChromaDB knowledge base created by `scripts/ingest_cv.py`.

This milestone intentionally stops at Markdown. PDF generation, web UI, job-site scraping, and advanced hallucination validation come later.

## Current Repo Context

Already implemented:

- `scripts/ingest_cv.py` loads CV PDFs and portfolio paths.
- `src/personal_cv_agent/pipeline.py` orchestrates ingestion.
- `src/personal_cv_agent/loaders.py` loads PDFs.
- `src/personal_cv_agent/portfolio_loader.py` loads portfolio README, HTML, and `src/data/*.ts`.
- `src/personal_cv_agent/transformers.py` cleans, chunks, and annotates section metadata.
- `src/personal_cv_agent/vector_store.py` writes to ChromaDB and exposes `as_retriever()`.
- `src/personal_cv_agent/config.py` defines vector DB, embedding, chunking, and retrieval defaults.

Milestone 2 should reuse those pieces. It should not create a second vector-store abstraction or duplicate ingestion logic.

## Architecture

Data flow:

```text
job.txt
  -> load raw job posting
  -> analyze requirements
  -> build section-specific retrieval queries
  -> retrieve evidence from ChromaDB
  -> plan CV sections
  -> generate Markdown CV
  -> run basic validation
  -> write output/custom_cv.md
```

Package shape after this milestone:

```text
src/personal_cv_agent/
  config.py
  loaders.py
  portfolio_loader.py
  transformers.py
  embeddings.py
  vector_store.py
  pipeline.py
  schemas.py          # new
  job_analysis.py     # new
  retrieval.py        # new
  planner.py          # new
  generator.py        # new
  validator.py        # new
scripts/
  ingest_cv.py
  generate_cv.py      # new
data/
  job_postings/
    example_data_engineer.txt # new sanitized example
output/
  .gitkeep            # optional, output markdown ignored later if needed
tests/
  test_job_analysis.py # new
  test_retrieval.py    # new
  test_validator.py    # new
```

## Files To Create

### `src/personal_cv_agent/schemas.py`

Purpose: shared Pydantic contracts for Milestone 2.

Classes:

```python
class JobAnalysis(BaseModel):
    role_title: str
    company: str | None
    location: str | None
    seniority: str | None
    role_family: RoleFamily
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    responsibilities: list[str]
    keywords: list[str]
    raw_text: str
```

```python
class RetrievalQuerySet(BaseModel):
    summary_query: str
    skills_query: str
    experience_query: str
    projects_query: str
    certifications_query: str
```

```python
class EvidenceItem(BaseModel):
    evidence_id: str
    content: str
    source_type: str
    source_file: str
    section: str
    relevance_area: Literal["summary", "skills", "experience", "projects", "certifications"]
```

```python
class EvidencePack(BaseModel):
    job: JobAnalysis
    queries: RetrievalQuerySet
    items: list[EvidenceItem]
```

```python
class CVPlan(BaseModel):
    target_title: str
    summary_angle: str
    skill_groups: list[str]
    experience_focus: list[str]
    project_focus: list[str]
    certification_focus: list[str]
    omitted_or_deemphasized: list[str]
```

```python
class MarkdownCV(BaseModel):
    markdown: str
    evidence_ids: list[str]
```

```python
class ValidationIssue(BaseModel):
    severity: Literal["warning", "error"]
    message: str
    section: str | None = None
```

```python
class ValidationReport(BaseModel):
    passed: bool
    issues: list[ValidationIssue]
    estimated_pages: float
    word_count: int
```

Also define:

```python
RoleFamily = Literal[
    "data_analyst",
    "data_engineer",
    "ai_engineer",
    "ml_engineer",
    "healthcare_ai",
    "product_ai",
    "consulting",
    "software_engineering",
    "unknown",
]
```

Expected input: Python values from other modules.

Expected output: validated typed objects.

Design note: Pydantic is recommended because it makes future LLM structured-output parsing much safer.

### `src/personal_cv_agent/job_analysis.py`

Purpose: load and analyze a job posting.

Functions/classes:

```python
def load_job_posting(path: Path) -> str:
    """Read a local .txt job posting and return normalized text."""
```

Input: `Path`.

Output: non-empty string.

Errors:

- `FileNotFoundError` if path does not exist.
- `ValueError` if file is empty.
- `ValueError` if suffix is not `.txt` for MVP.

```python
class RuleBasedJobAnalyzer:
    def analyze(self, raw_text: str) -> JobAnalysis:
        """Create a conservative JobAnalysis without requiring an LLM."""
```

Input: raw job text.

Output: `JobAnalysis`.

Behavior:

- Infer `role_title` from first non-empty line or from common title patterns.
- Infer `role_family` with keyword matching.
- Extract skills from a fixed vocabulary plus capitalized technical terms.
- Extract responsibilities from lines containing verbs such as build, analyze, design, develop, maintain, collaborate, validate.
- Preserve `raw_text`.

Why rule-based first:

- Keeps MVP runnable without an API key.
- Avoids early complexity.
- Gives stable tests.

Future extension:

```python
class LLMJobAnalyzer:
    def analyze(self, raw_text: str) -> JobAnalysis:
        """Use an LLM with structured output when OPENAI_API_KEY is available."""
```

Do not implement `LLMJobAnalyzer` unless the MVP needs it. The blueprint allows it later.

### `src/personal_cv_agent/retrieval.py`

Purpose: turn job analysis into targeted retrieval queries and fetch evidence from ChromaDB.

Functions/classes:

```python
def build_retrieval_queries(job: JobAnalysis) -> RetrievalQuerySet:
    """Create section-specific retrieval queries from job requirements."""
```

Input: `JobAnalysis`.

Output: `RetrievalQuerySet`.

Query design:

- `summary_query`: role title + role family + must-have skills.
- `skills_query`: must-have and nice-to-have skills.
- `experience_query`: responsibilities + role family.
- `projects_query`: domain + tools + outcomes.
- `certifications_query`: certifications, cloud, language, SAP, research, healthcare, or domain signals.

```python
class EvidenceRetriever:
    def __init__(self, config: IngestionConfig) -> None: ...
    def retrieve(self, job: JobAnalysis) -> EvidencePack: ...
```

Input: `IngestionConfig`, `JobAnalysis`.

Output: `EvidencePack`.

Implementation detail:

- Reuse `ChromaVectorStore(config).as_retriever()`.
- Run each query separately.
- Convert returned `Document` objects into `EvidenceItem`.
- Use a stable `evidence_id`, for example `E1`, `E2`, etc.
- Deduplicate by `(source_file, section, content[:120])`.
- Keep the retrieved `section`, `source_type`, and `source_file` metadata.

Basic retrieval count:

- Start with 5 documents per section query.
- Deduplicate and cap final evidence pack at around 20 items.

Errors:

- If Chroma DB directory does not exist: raise a clear `RuntimeError` telling the user to run ingestion first.
- If no evidence is retrieved: raise `RuntimeError` with recovery steps.

### `src/personal_cv_agent/planner.py`

Purpose: decide what the CV should emphasize before writing Markdown.

Functions/classes:

```python
class CVPlanner:
    def create_plan(self, evidence_pack: EvidencePack) -> CVPlan:
        """Create a conservative CV plan from job analysis and retrieved evidence."""
```

Input: `EvidencePack`.

Output: `CVPlan`.

MVP behavior:

- Rule-based, not LLM-heavy.
- Select target title from job role title.
- Build `summary_angle` using role family:
  - data engineering: SQL, ETL, DWH, validation, AWS.
  - AI/RAG: RAG, FAISS, Hugging Face, LLM apps, prompt engineering.
  - ML: Python, model evaluation, LightGBM/TensorFlow, geospatial/computer vision.
  - healthcare AI: biomedical AI, transparency, model reliability.
  - consulting: SAP, stakeholder communication, analytics delivery.
- Select skills from evidence and job must-haves.
- Select project focus only when retrieved evidence supports the project.
- List omitted/deemphasized areas to keep output concise.

Why planning matters:

- It creates a checkpoint before generation.
- It reduces hallucination pressure.
- It makes future debugging easier.

### `src/personal_cv_agent/generator.py`

Purpose: generate a Markdown CV draft from the plan and evidence.

Functions/classes:

```python
class MarkdownCVGenerator:
    def generate(self, plan: CVPlan, evidence_pack: EvidencePack) -> MarkdownCV:
        """Generate ATS-friendly Markdown from plan and evidence."""
```

Input: `CVPlan`, `EvidencePack`.

Output: `MarkdownCV`.

MVP generation strategy:

- Template-assisted generation.
- Use retrieved evidence text directly or conservatively paraphrased.
- Prefer compact bullets.
- Avoid unsupported metrics.
- Add an internal evidence comment after sections only if useful for debugging, but final user-facing CV should not expose noisy IDs unless `--include-evidence-ids` is passed.

Recommended Markdown sections:

```markdown
# Rana Irem Turhan

Istanbul, Turkey | email | LinkedIn | GitHub | Portfolio

## Summary

## Technical Skills

## Experience

## Selected Projects

## Education

## Certifications
```

Length rules:

- Summary: 2-3 lines.
- Skills: 4-7 grouped lines.
- Experience: 2-4 bullets per role.
- Projects: 2-4 projects, 1-2 bullets each.
- Certifications: only relevant or core credentials.

This should fit roughly within a two-page CV when later rendered.

### `src/personal_cv_agent/validator.py`

Purpose: basic validation for MVP, designed to grow into stronger hallucination control later.

Functions/classes:

```python
class BasicCVValidator:
    def validate(self, cv: MarkdownCV, evidence_pack: EvidencePack) -> ValidationReport:
        """Run basic length, structure, and evidence-safety checks."""
```

Input: `MarkdownCV`, `EvidencePack`.

Output: `ValidationReport`.

Checks:

- Markdown is not empty.
- Required sections exist: Summary, Technical Skills, Experience, Selected Projects.
- Word count is below a configurable threshold, e.g. 850-1100 words.
- Estimated pages <= 2.0 using a simple heuristic, e.g. `word_count / 475`.
- No obvious unsupported danger phrases:
  - "led" when evidence does not include led/leading/lead.
  - percentages or numbers not present in evidence text.
  - company names not present in evidence text.
  - tools not present in evidence text or job posting.
- Warn if no evidence items were used.

For this milestone:

- Validator can produce warnings instead of blocking all output.
- If `--strict` is passed, validation errors should stop writing the final CV.

### `scripts/generate_cv.py`

Purpose: user-facing CLI for Milestone 2.

Functions:

```python
def parse_args() -> argparse.Namespace: ...
def build_config(args: argparse.Namespace) -> IngestionConfig: ...
def main() -> None: ...
```

CLI command:

```bash
python scripts/generate_cv.py --job-posting data/job_postings/job.txt --output output/custom_cv.md
```

Arguments:

- `--job-posting Path`: required.
- `--output Path`: required.
- `--vector-db-dir Path`: optional override, default from env/config.
- `--embedding-provider {openai,huggingface}`: optional override matching ingestion script.
- `--strict`: optional, fail if validator reports errors.
- `--include-evidence-ids`: optional, append evidence references for debugging.

CLI flow:

1. `load_dotenv()`.
2. Read args.
3. Build `IngestionConfig`.
4. Load job posting.
5. Analyze job.
6. Retrieve evidence from Chroma.
7. Create CV plan.
8. Generate Markdown CV.
9. Validate.
10. Create output directory if needed.
11. Write Markdown file.
12. Print summary:
    - role title
    - role family
    - evidence items retrieved
    - output path
    - validation status

### `data/job_postings/example_data_engineer.txt`

Purpose: sanitized sample job posting for demos and tests.

This file must not contain a real private application.

Example content is provided later in this document.

### `tests/test_job_analysis.py`

Purpose: test rule-based job analysis.

Test cases:

- Data engineer posting detects `data_engineer`.
- AI engineer posting detects `ai_engineer`.
- Empty posting raises `ValueError`.
- Skills extraction captures SQL, Python, AWS, ETL, Power BI where present.

### `tests/test_retrieval.py`

Purpose: test query construction without requiring real Chroma.

Test cases:

- `build_retrieval_queries()` returns non-empty section queries.
- Must-have skills appear in at least one query.
- Role title appears in summary query.

Do not require private CV files in tests.

### `tests/test_validator.py`

Purpose: test basic Markdown checks.

Test cases:

- Missing Summary creates warning/error.
- Very long Markdown estimates >2 pages.
- Unsupported number warning triggers if a number appears in CV but not evidence.

## Files To Modify

### `pyproject.toml`

Add dependencies:

```toml
"pydantic>=2.0.0",
```

Optional but useful later:

```toml
"langchain-core>=0.2.0",
```

Do not add heavy PDF, UI, or web-scraping dependencies in this milestone.

### `requirements.txt`

Add:

```text
pydantic>=2.0.0
```

Keep dependency changes minimal.

### `README.md`

Add a short Milestone 2 usage section after ingestion docs:

```markdown
## Generate A Markdown CV

After ingesting CV and portfolio sources:

```bash
python scripts/generate_cv.py --job-posting data/job_postings/example_data_engineer.txt --output output/custom_cv.md
```
```

Mention that Markdown generation requires an existing ChromaDB knowledge base.

### `src/personal_cv_agent/__init__.py`

Optional.

Can export:

```python
from personal_cv_agent.schemas import JobAnalysis, CVPlan, EvidencePack
```

Avoid exporting every class. Keep public API small.

### `.gitignore`

Consider adding:

```text
output/*.md
!output/.gitkeep
data/chroma/
```

Current `.gitignore` already excludes `data/chroma/` and `output/`. If examples are needed, use `examples/outputs/` or commit only `.gitkeep`.

## Expected Inputs And Outputs

### Job Analysis

Input:

- Raw job posting text from `.txt`.

Output:

- `JobAnalysis` with role family, skills, responsibilities, and keywords.

### Retrieval

Input:

- `JobAnalysis`.
- Existing ChromaDB directory.

Output:

- `EvidencePack` containing retrieved, deduplicated evidence items.

### Planning

Input:

- `EvidencePack`.

Output:

- `CVPlan` describing what the CV should emphasize.

### Generation

Input:

- `CVPlan`.
- `EvidencePack`.

Output:

- `MarkdownCV`.

### Validation

Input:

- `MarkdownCV`.
- `EvidencePack`.

Output:

- `ValidationReport`.

### CLI

Input:

```bash
python scripts/generate_cv.py --job-posting data/job_postings/example_data_engineer.txt --output output/custom_cv.md
```

Output:

- Markdown file written to `output/custom_cv.md`.
- Console summary of generation and validation.

## Error Handling Strategy

### Missing Job Posting

Raise:

```text
Job posting not found: <path>
```

Recovery:

- Ask user to provide a valid `.txt` file.

### Empty Job Posting

Raise:

```text
Job posting is empty: <path>
```

Recovery:

- Add job description text.

### Missing ChromaDB

Raise:

```text
No ChromaDB knowledge base found at <path>. Run scripts/ingest_cv.py first.
```

Recovery:

- Run ingestion with CV and portfolio sources.

### Missing Embedding Credentials

If OpenAI embeddings are configured but `OPENAI_API_KEY` is absent, the embedding model will fail.

Recovery message:

```text
OpenAI embeddings require OPENAI_API_KEY. Add it to .env or use --embedding-provider huggingface.
```

### No Evidence Retrieved

Raise:

```text
No relevant evidence was retrieved. Check that ingestion completed and the job posting contains enough detail.
```

Recovery:

- Re-run ingestion.
- Try a richer job posting.
- Inspect vector DB path.

### Validation Failure

Default:

- Write output with warnings printed.

With `--strict`:

- Do not write output if validation has errors.

### Output Path Failure

Behavior:

- Create parent directory automatically.
- If path cannot be written, raise a clear filesystem error.

## Simple Test Cases

### `test_job_analysis_detects_data_engineer`

Input:

```text
Data Engineer
We need SQL, Python, AWS, ETL pipelines, data warehouse modeling, and data quality validation.
```

Expected:

- `role_family == "data_engineer"`.
- `SQL`, `Python`, `AWS`, `ETL` appear in skills/keywords.

### `test_job_analysis_detects_ai_engineer`

Input:

```text
AI Engineer
Build RAG applications using vector search, embeddings, LLMs, prompt engineering, and Python.
```

Expected:

- `role_family == "ai_engineer"`.
- `RAG`, `vector search`, `LLMs`, `Python` appear.

### `test_empty_job_posting_fails`

Input:

- Empty file.

Expected:

- `ValueError`.

### `test_retrieval_queries_include_job_terms`

Input:

- `JobAnalysis` with role title `Data Engineer` and skills `SQL`, `AWS`.

Expected:

- Summary query includes `Data Engineer`.
- Skills or experience query includes `SQL` and `AWS`.

### `test_validator_detects_missing_sections`

Input:

```markdown
# Rana Irem Turhan

Some text only.
```

Expected:

- Validation report has warning/error for missing sections.

### `test_validator_warns_on_unsupported_number`

Evidence:

```text
Worked on ETL validation using SQL and Python.
```

CV:

```text
Improved ETL performance by 40%.
```

Expected:

- Validation warning/error for unsupported `40%`.

## Example `job.txt`

Create as `data/job_postings/example_data_engineer.txt`:

```text
Data Engineer Intern

We are looking for a Data Engineer Intern to support analytics and data platform projects. The role involves building and validating ETL pipelines, writing SQL queries, improving data quality checks, and supporting data warehouse models for reporting and business intelligence.

Responsibilities:
- Develop and maintain SQL-based data transformations.
- Support ETL pipeline validation and data reconciliation.
- Work with PostgreSQL or similar relational databases.
- Collaborate with analytics and BI teams to ensure reliable reporting.
- Document data quality issues and communicate findings clearly.

Required skills:
- SQL
- Python
- ETL pipelines
- Data warehousing
- PostgreSQL
- Data quality validation

Nice to have:
- AWS
- Power BI
- Git
- Agile collaboration
```

## Example Generated Markdown CV Structure

```markdown
# Rana Irem Turhan

Istanbul, Turkey | ranairemturhan@gmail.com | LinkedIn | GitHub | Portfolio

## Summary

Early-career Data Analytics Engineering and Applied AI practitioner with hands-on experience in SQL-based data validation, ETL testing, data warehousing, and Python-supported analytics workflows. Experienced with PostgreSQL, data quality checks, Power BI, AWS services, and cross-functional analytics delivery.

## Technical Skills

- Programming & Querying: SQL, Python
- Data Engineering: ETL/ELT pipelines, data warehousing, data modeling, reconciliation, data quality validation
- Databases & BI: PostgreSQL, Power BI, DBeaver
- Cloud & Tools: AWS, Git, GitHub, Jira
- AI/ML Context: RAG systems, FAISS, Hugging Face, Scikit-learn

## Experience

### Data Analytics Engineering Trainee - EPAM Systems

- Worked with multi-layer data warehouse architectures including landing, normalized, and data mart layers for analytics workflows.
- Performed source-to-target reconciliation and data quality validation using SQL and Python.
- Developed SQL logic with joins, CTEs, window functions, and transaction-control concepts for analytical data processing.
- Supported ETL, DWH, and dashboard testing by validating completeness, consistency, transformation rules, and KPI outputs.

### Technical Community Lead & AI Content Creator - Data Science & ML Hub

- Created practical educational content on ETL pipelines, data quality, analytics engineering, machine learning, and applied AI.
- Organized and moderated technical events and knowledge-sharing sessions for students and early-career professionals.

## Selected Projects

### Multi-layer Data Warehouse Case Study

- Designed a staging-to-data-mart workflow using SQL, PostgreSQL, ETL concepts, and data quality checks.

### RAG-Based SQL Chatbot

- Built a retrieval-augmented application for natural-language interaction with SQL knowledge sources using Python, FAISS, Hugging Face, and an LLM API.

## Education

Bachelor of Engineering Science in Computer Systems - Riga Technical University

## Certifications

- SAP Certified Associate - Implementation Consultant
- SAP Generative AI Developer
- SQL Intermediate - HackerRank
- IELTS Academic 7.5 / CEFR C1
```

Notes:

- The exact content must come from retrieved evidence.
- The generator should not include the sample bullets unless evidence supports them.
- Contact links should eventually come from a profile source, not hardcoded forever.

## Recommended Commit Sequence

### Commit 1: Add Milestone 2 schemas

Files:

- `src/personal_cv_agent/schemas.py`
- `pyproject.toml`
- `requirements.txt`

Message:

```text
Add CV generation schemas
```

### Commit 2: Add job posting analysis

Files:

- `src/personal_cv_agent/job_analysis.py`
- `data/job_postings/example_data_engineer.txt`
- `tests/test_job_analysis.py`

Message:

```text
Add job posting analysis
```

### Commit 3: Add evidence retrieval

Files:

- `src/personal_cv_agent/retrieval.py`
- `tests/test_retrieval.py`

Message:

```text
Add job-aware evidence retrieval
```

### Commit 4: Add CV planning and Markdown generation

Files:

- `src/personal_cv_agent/planner.py`
- `src/personal_cv_agent/generator.py`

Message:

```text
Add Markdown CV planning and generation
```

### Commit 5: Add basic validation and CLI

Files:

- `src/personal_cv_agent/validator.py`
- `scripts/generate_cv.py`
- `tests/test_validator.py`

Message:

```text
Add Markdown CV generator CLI
```

### Commit 6: Update documentation

Files:

- `README.md`
- `docs/MILESTONE_2_BLUEPRINT.md` if refinements are needed

Message:

```text
Document Markdown CV generation workflow
```

## Connection To Existing Ingestion Pipeline

Milestone 2 depends on Milestone 1 in this exact way:

1. User runs `scripts/ingest_cv.py` with CV PDFs and portfolio sources.
2. Existing pipeline loads, cleans, chunks, embeds, and stores documents in ChromaDB.
3. `scripts/generate_cv.py` loads the same `IngestionConfig`.
4. `EvidenceRetriever` uses `ChromaVectorStore(config).as_retriever()`.
5. Retrieved chunks preserve metadata created during ingestion:
   - `source_type`
   - `source_file`
   - `source_path`
   - `section`
   - `chunk_id`
6. Generator uses those chunks as evidence for Markdown CV content.

This means Milestone 2 should not re-read CV PDFs directly. It should trust the knowledge base as the source of career evidence.

## Intentionally Excluded From This Milestone

Do not build:

- PDF generation.
- DOCX generation.
- Web UI.
- Streamlit UI.
- Job board scraping.
- Browser automation.
- Authentication.
- Cloud deployment.
- Fine-tuning.
- Vector DB evaluation framework.
- Advanced reranking.
- Multi-agent orchestration.
- User feedback learning loop.
- Long-term memory of accepted CV versions.
- Automatic upload of CVs, generated outputs, or Chroma data to GitHub.

Also avoid:

- Hardcoding private CV facts into source code.
- Committing real job applications.
- Committing generated CVs with private contact details.
- Building complex LLM chains before the rule-based MVP works.

## Implementation Principles

- Keep the MVP deterministic where possible.
- Prefer small modules with clear inputs and outputs.
- Make every generated claim traceable to evidence later, even if the MVP validator is basic.
- Fail with helpful messages.
- Keep Markdown clean, compact, and ATS-friendly.
- Preserve the user's credibility by refusing unsupported embellishment.
- Make the repo understandable to junior engineers while still demonstrating serious RAG design.

## Next Prompt For Implementation

When ready to implement, use this prompt:

```text
Implement Milestone 2 according to docs/MILESTONE_2_BLUEPRINT.md. Start with schemas, job posting analysis, retrieval query construction, basic planning, Markdown generation, validation, and scripts/generate_cv.py. Keep the implementation minimal and testable. Do not add PDF generation. Do not commit private CV files or generated private outputs.
```

## Summary

Created file:

- `docs/MILESTONE_2_BLUEPRINT.md`

Why this is the correct next step:

- The ingestion and memory layer already exists.
- The next product risk is not PDF styling; it is job-aware retrieval, evidence selection, and hallucination-safe Markdown generation.
- A blueprint prevents the next sprint from becoming too broad and keeps the system aligned with the GitHub portfolio goal.

What to implement next:

- `scripts/generate_cv.py`
- `schemas.py`
- `job_analysis.py`
- `retrieval.py`
- `planner.py`
- `generator.py`
- `validator.py`
