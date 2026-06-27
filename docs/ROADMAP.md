# Product And Technical Roadmap

## Product Vision

Portfolio CV LLM Agent is a personal, evidence-grounded CV generation system. It is designed to help an early-career data analytics and applied AI engineer turn real career artifacts into role-specific, ATS-friendly CV drafts without inventing claims.

The strategic value is not "another CV writer." The differentiator is evidence control:

- The system only writes claims grounded in ingested CV, portfolio, project, certification, and research evidence.
- The system adapts emphasis by job type: Data Analyst, Data Engineer, AI Engineer, ML Engineer, Healthcare AI, Product/AI Builder, or Consultant.
- The system creates a reusable personal career knowledge base instead of starting from a blank prompt for every application.
- The GitHub project demonstrates practical RAG engineering: ingestion, retrieval, planning, validation, and structured generation.

## Current State

Implemented:

- PDF CV ingestion.
- Portfolio source ingestion for README, HTML, and `src/data/*.ts`.
- Text cleaning and section-aware chunking.
- Local ChromaDB persistence.
- OpenAI embedding support with optional Hugging Face backend.
- MMR retriever configuration.
- CLI ingestion script.

Missing:

- Job posting input.
- Job requirement extraction.
- Evidence retrieval by CV section.
- CV planning.
- Markdown CV generation.
- Evidence validation / hallucination control.
- Two-page length control.
- PDF rendering.

## Core Architecture

The system should remain modular:

```text
career_sources -> ingestion -> vector_store
job_posting -> job_analysis -> retrieval -> cv_planning -> generation -> validation -> markdown_cv
```

Recommended package structure:

```text
src/personal_cv_agent/
  config.py
  loaders.py
  portfolio_loader.py
  transformers.py
  embeddings.py
  vector_store.py
  pipeline.py
  job_analysis.py       # Parse job postings into structured requirements
  retrieval.py          # Build targeted retrieval queries
  schemas.py            # Typed data contracts
  planner.py            # Decide what to include/omit
  generator.py          # Generate Markdown CV from plan + evidence
  validator.py          # Check evidence grounding and length constraints
scripts/
  ingest_cv.py
  generate_cv.py
examples/
  job_postings/
  outputs/
docs/
```

## MVP Definition

The true MVP is:

```bash
python scripts/generate_cv.py --job-posting job.txt --output output/custom_cv.md
```

It should:

1. Read a job posting from a local `.txt` file.
2. Extract structured job requirements.
3. Retrieve relevant evidence from ChromaDB.
4. Produce a concise CV plan.
5. Generate an ATS-friendly Markdown CV.
6. Validate that generated bullets are supported by retrieved evidence.
7. Refuse or flag unsupported claims instead of inventing.

MVP should not:

- Generate PDF yet.
- Scrape job sites.
- Build a web UI.
- Fine-tune a model.
- Upload private CV data to GitHub.
- Try to optimize every possible resume style.

Markdown first keeps the system testable. PDF rendering comes after content quality is reliable.

## Data Schemas

Use dataclasses or Pydantic models to make LLM outputs predictable.

### JobAnalysis

```python
class JobAnalysis(BaseModel):
    role_title: str
    company: str | None = None
    domain: str | None = None
    seniority: str | None = None
    must_have_skills: list[str]
    nice_to_have_skills: list[str]
    responsibilities: list[str]
    keywords: list[str]
    role_family: Literal[
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

### EvidenceChunk

```python
class EvidenceChunk(BaseModel):
    content: str
    source_type: str
    source_file: str
    section: str
    relevance_reason: str
```

### CVPlan

```python
class CVPlan(BaseModel):
    target_role: str
    positioning_summary: str
    selected_skills: list[str]
    selected_experience_ids: list[str]
    selected_project_ids: list[str]
    selected_certifications: list[str]
    omitted_items: list[str]
    evidence_ids: list[str]
```

### ValidatedBullet

```python
class ValidatedBullet(BaseModel):
    text: str
    evidence_ids: list[str]
    confidence: Literal["high", "medium", "low"]
    validation_notes: str
```

## Hallucination Control

This is the most important feature.

Validation should happen in layers:

1. Retrieval grounding: every section of the generated CV must receive retrieved evidence.
2. Structured planning: the LLM must choose from evidence before writing prose.
3. Evidence IDs: generated bullets should carry source chunk references internally.
4. Claim scanner: check for numbers, company names, tools, awards, dates, and project names.
5. Unsupported-claim policy: delete or flag unsupported claims.

Allowed behavior:

- Rephrase verified facts.
- Reorder verified skills.
- Emphasize verified experience differently by role.
- Combine related evidence if both sources support it.

Forbidden behavior:

- Inventing metrics.
- Inventing repositories or demos.
- Turning "worked on" into "led" unless evidence says leadership.
- Adding tools not present in evidence.
- Claiming production deployment without evidence.
- Making private/internal projects look public.

Confidence scoring:

- `high`: exact evidence supports the claim.
- `medium`: claim is a conservative synthesis of multiple evidence chunks.
- `low`: claim is plausible but weakly supported; should not appear in final CV without user review.

The MVP should only include `high` and conservative `medium` claims.

## Retrieval Strategy

Do not retrieve once for the whole CV. Use targeted retrieval:

- Summary query: role title + must-have skills + domain.
- Skills query: required tools and methods.
- Experience query: responsibilities + role family.
- Projects query: domain + technical stack + outcomes.
- Certifications/research query: domain + required credibility signals.

Use metadata filters when useful:

- `section="experience"` for experience bullets.
- `section="projects"` for selected projects.
- `source_type="portfolio"` for project detail.
- `source_type="cv_pdf"` for formal CV phrasing.

MMR retrieval is useful because it reduces duplicated chunks and gives broader evidence coverage.

## Prompt Chain Design

### 1. Job Analysis Prompt

Input: raw job posting.

Output: `JobAnalysis`.

Failure mode: job posting is vague or malformed.

Guardrail: ask the model to preserve exact required skill names and avoid adding implied requirements.

### 2. Retrieval Query Prompt

Input: `JobAnalysis`.

Output: retrieval queries grouped by section.

Failure mode: generic queries retrieve weak evidence.

Guardrail: require concrete terms from the job posting.

### 3. CV Planning Prompt

Input: `JobAnalysis` + retrieved evidence.

Output: `CVPlan`.

Failure mode: plan includes too much.

Guardrail: max 3-4 projects, max 6-10 skill clusters, omit weakly relevant content.

### 4. Markdown Generation Prompt

Input: `CVPlan` + evidence.

Output: Markdown CV.

Failure mode: invented bullets or bloated text.

Guardrail: no claim without evidence. Use concise ATS format.

### 5. Validation Prompt

Input: Markdown CV + evidence.

Output: unsupported claims, weak claims, repeated bullets, missing job keywords.

Failure mode: validator becomes too lenient.

Guardrail: validator should be strict and prefer deletion over unsupported embellishment.

## Personalization Strategy

For the first version, user preferences should be config-driven, not learned automatically.

Example:

```yaml
tone: professional_direct
max_pages: 2
preferred_order:
  - summary
  - skills
  - experience
  - projects
  - education
  - certifications
avoid:
  - exaggerated claims
  - unsupported leadership language
  - dense paragraphs
default_role_targets:
  - data_engineer
  - applied_ai
  - analytics_engineering
```

Later, add a `profile.yaml` that stores preferred title variants, target roles, and projects the user wants to emphasize.

## Role-Based Emphasis

Data Analyst / Analytics Engineering:

- EPAM data quality, reconciliation, PostgreSQL, Power BI, AWS, ETL/DWH testing.
- Climate dashboard and analytics projects.
- Business-facing communication and reporting.

Data Engineer:

- Multi-layer DWH, Landing/3NF/Data Mart, SQL validation, ETL reliability.
- AWS services, PostgreSQL, data modeling.
- DWH case study.

AI Engineer / RAG:

- RAG SQL chatbot, FAISS, Hugging Face, LLM integration, prompt engineering.
- Microsoft AI internship, AI agents, Azure AI ecosystem.
- CV LLM Agent itself once mature.

ML Engineer:

- Paint Factory process prediction, LightGBM, leakage-safe validation, MAE improvement.
- Polar GIS, TensorFlow/Keras, computer vision, geospatial workflows.

Healthcare AI:

- TEKNOFEST VEGA, clinical genomics, model reliability.
- ICADA research, transparency and auditability.

Product / AI Builder:

- FoodVision AI, user flows, MVP scoping, responsible AI.
- Municipal AI assistant and AI assessment pilot.

Consulting:

- SAP certifications, stakeholder communication, business process translation.
- EPAM enterprise data workflows and analytics validation.

## Phased Roadmap

### Phase 1: Markdown CV MVP

- Add `schemas.py`.
- Add `job_analysis.py`.
- Add `retrieval.py`.
- Add `planner.py`.
- Add `generator.py`.
- Add `validator.py`.
- Add `scripts/generate_cv.py`.
- Generate Markdown only.

Done when a job posting produces a usable, evidence-grounded Markdown CV draft.

### Phase 2: Quality And Testing

- Unit tests for job parsing and schemas.
- Golden test job postings for Data Analyst, AI Engineer, ML Engineer.
- Validation reports.
- Unsupported-claim detection.
- Basic length scoring for two-page feasibility.

Done when generated CVs are consistent, concise, and mostly ready for manual polish.

### Phase 3: PDF Rendering

- Convert validated Markdown to PDF.
- Use a simple ATS-friendly template.
- Render and check page count.
- Add compression loop if output exceeds two pages.

Done when the system outputs a polished two-page PDF.

### Phase 4: Portfolio-Grade Features

- Add example sanitized job postings and generated outputs.
- Add architecture diagrams.
- Add retrieval evaluation.
- Add CLI demo workflow.
- Add GitHub Actions checks.

Done when the repo clearly demonstrates RAG/product engineering skill without exposing private data.

### Phase 5: Advanced Personalization

- Add `profile.yaml`.
- Add role-specific templates.
- Add feedback loop: user accepts/rejects bullets.
- Add local history of successful CV versions.

Done when the tool starts adapting to user preferences over time.

## Immediate Next Module

Build `scripts/generate_cv.py` plus minimal supporting modules.

First implementation should:

1. Accept `--job-posting`.
2. Accept `--output`.
3. Load the Chroma retriever.
4. Analyze the job posting.
5. Retrieve evidence.
6. Generate a Markdown CV draft.
7. Write output to `output/custom_cv.md`.

Use deterministic fallbacks where possible. If no LLM key is available, still support a retrieval summary mode so the CLI can prove the pipeline is connected.

## Suggested Development Order

1. Add schemas.
2. Add raw job posting loader.
3. Add simple LLM job analyzer.
4. Add retrieval query builder.
5. Add evidence pack formatter.
6. Add Markdown generator.
7. Add strict validator.
8. Add tests.
9. Add examples.
10. Push a new GitHub commit.

This keeps the project impressive but still achievable.
