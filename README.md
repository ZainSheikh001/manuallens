# ManualLens

Ask repair questions about equipment manuals and get answers with the exact
values and the source page. Pages are searched as images, so diagrams, tables
and exploded views are retrievable.

Status: week 1 of 8. See `docs/PRD.md` for the full specification and
`docs/working-agreement.md` for how the project is being built.

## Setup

Requirements: Python 3.11+, [uv](https://docs.astral.sh/uv/), Docker.

```bash
uv sync
cp .env.example .env
docker compose up -d
uv run pytest
```

## Data

Manuals are not stored in this repository. Add rows to `data/manifest.csv`, then:

```bash
uv run python -m assistant.ingest.download
uv run python -m assistant.ingest.render
```

## Results

Results tables will be added here as each experiment in the evaluation plan is run.
