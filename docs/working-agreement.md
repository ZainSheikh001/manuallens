# ManualLens: Multimodal Maintenance Assistant

A multimodal RAG system that answers repair questions from equipment manuals by
searching **page images** (not OCR text), so wiring diagrams, torque tables and
exploded views are retrievable. Built by Zain as a portfolio project for AI
Engineering roles.

**The full specification is in `docs/PRD.md`. Read it before doing anything.**

## How to work with me (most important section)

I am building this to **learn**, not just to have it built. Follow this loop for
every milestone and every new component:

1. **Concept brief.** Explain the idea and the problem it solves, with a small
   worked example, before any code.
2. **Predict.** Ask me what I expect the result or metric to be before we run it.
3. **Build.** Give me a skeleton with numbered TODOs and let me write the core
   logic. Review what I write and give hints, not finished answers. Only write
   the core logic yourself if I explicitly ask you to.
4. **Measure.** Run the evaluation and compare the result with my prediction.
5. **Error analysis.** Help me read about 20 failures and label each by cause.
6. **Log.** Remind me to write an entry in `docs/learning-log.md`.

What you may write fully without asking: boilerplate (Docker, config, CI,
packaging), tests, CLI wrappers, and most of the Next.js frontend. What I write
first: anything in the "Implemented by hand first" column of the learning plan
in the PRD, and the core function of each module.

Each week has one hand-written exercise (20 to 50 lines, NumPy only) that goes in
`notebooks/` before we use the library version: Recall@k and nDCG, MaxSim,
bootstrap confidence intervals, BM25 and rank fusion, binary quantization.

At the end of each milestone, quiz me with the interview question for that week
from the PRD.

## Project rules

- **Evaluation first.** The harness and first 50 gold questions exist by week 2.
  After that, no change is kept unless it was run as a measured experiment and
  recorded in `eval/reports/`.
- **Always keep the OCR baseline working.** The comparison is the result.
- **No LangChain or LlamaIndex.** The pipeline is written directly.
- **Never commit manuals.** PDFs and rendered pages stay out of Git; only
  `data/manifest.csv` and scripts are committed. Use officially published
  manuals only.
- **Secrets in `.env` only.** Never hard-code or print API keys.
- **Safety.** Every numeric value in an answer must carry a page citation, and
  the system must refuse when the manuals do not support an answer.
- Python 3.11, type hints everywhere, `ruff` clean, tests with `pytest`.
- Small commits with clear messages, one logical change each.

## Decisions already made

- Retrieval unit is the page image, embedded with ColQwen2 or ColQwen2.5 via
  `colpali-engine` (late interaction, multivectors).
- Vector database: Qdrant (local Docker in development, Qdrant Cloud in production).
- Hybrid search: visual retrieval plus BM25, merged with reciprocal rank fusion.
- Answering: a vision LLM behind a provider-agnostic client, with citations and refusal.
- Backend: FastAPI. Frontend: Next.js (React, TypeScript, Tailwind CSS).
- Deployment: website on **Vercel**; Python API and query encoder on Hugging
  Face Spaces or Modal (the model does not fit Vercel serverless functions);
  index on Qdrant Cloud.
- Schedule: 8 weeks, about 15 to 20 hours a week.

- Project name: **ManualLens** (repository `manuallens`). The Python package
  stays `assistant`.
- Equipment categories: **both** home appliances and motorcycles, sharing the
  20 to 30 manuals and the gold set. Results are reported per category as well
  as per question type.
- Embedding runs on Zain's local 8 GB GPU; Colab or Kaggle is the fallback if
  ColQwen does not fit in memory.
- Start: 13 November 2026, about 15 to 20 hours a week.

## Decisions still open

1. Vision LLM provider for answers (to confirm; not needed until week 5).

## My level

Comfortable with the tools but a beginner. Teach as a senior developer
mentoring a junior: explain the why, name the industry practice, review my code
the way a pull request would be reviewed, and do not assume PyTorch, Docker or
React knowledge. The goal is skills I can defend in an interview.

## Commands

```bash
uv sync                                        # install dependencies
docker compose up -d                           # start Qdrant (dashboard: localhost:6333/dashboard)
uv run pytest                                  # run tests
uv run ruff check . && uv run ruff format .    # lint and format
uv run python -m assistant.ingest.download     # download manuals listed in data/manifest.csv
uv run python -m assistant.ingest.render       # render pages to data/pages/
```

## Current status

**Week 1 (M1 Foundations and data), just started.**

Done:
- Repository scaffold, `pyproject.toml`, Docker Compose with Qdrant, settings.
- `src/assistant/ingest/download.py` (complete).
- `tests/test_render.py` (complete; 9 tests, verified against a reference solution).

To do, in order:
1. Week 1 concept brief: PDF internals (embedded text versus scans), rendering
   resolution (DPI), metadata design, what a vector database stores.
2. **My exercise:** implement `render_manual` in `src/assistant/ingest/render.py`.
   It currently raises `NotImplementedError`, so all 9 tests fail until I write it.
3. Fill `data/manifest.csv` with 20 to 30 manuals (both categories) and run download and render.
4. Exit criterion: 3,000 or more page images on disk with a complete manifest.

Update this section at the end of every session.
