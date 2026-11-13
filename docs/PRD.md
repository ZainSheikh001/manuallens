# PRD: ManualLens (Multimodal Maintenance Assistant)

Owner: Zain. Written 12 November 2026, updated 13 November 2026.

## 1. Summary

The Multimodal Maintenance Assistant answers repair questions from equipment
manuals by searching page images directly, so wiring diagrams, torque tables and
exploded views are retrievable. A technician types a question, enters an error
code, or uploads a photo of a part, and gets the procedure, the exact values,
and the source page beside the answer.

**Problem.** Manuals run to hundreds of pages, and the information a technician
needs most sits in diagrams and tables. Standard RAG pipelines extract text with
OCR first, which scrambles tables and discards drawings, so those pages are
never found.

**Approach.** Each page is embedded as an image with a late-interaction vision
model (ColQwen family), combined with keyword search for exact codes, and
answered by a vision LLM that must cite the page it used.

**Why this project.** It is a portfolio project for AI Engineering roles. It
shows multimodal retrieval, hybrid search, grounded generation, measured
evaluation against a baseline, and deployment with cost and latency numbers.

## 2. Goals and success metrics

**Goals**

- Retrieve the correct manual page for text, table, diagram and error-code questions.
- Answer with exact values and a page citation, and refuse when the manuals do not contain the answer.
- Accept a photo of a part as a query.
- Publish a reproducible benchmark comparing the visual pipeline with an OCR baseline.
- Ship a public website, a repository and a results write-up.
- Zain can explain, implement and measure every component (see the learning plan).

**Non-goals**

- Fine-tuning or training a retrieval model.
- Real-time video or augmented-reality guidance.
- A mobile app, user accounts or multi-tenant access control.
- More than two equipment categories in v1.
- LangChain or LlamaIndex. The pipeline is written directly.

**Success metrics.** Initial targets, to be revised once the baseline is measured in week 2.

| Metric | Target | Measured on |
| --- | --- | --- |
| Page Recall@5, all questions | 85% or higher | Gold test set |
| Recall@5 gain over OCR baseline, diagram and table questions | 15 points or more | Gold test set subset |
| Numeric exact match (torque, clearances, part numbers) | 90% or higher when the correct page is retrieved | Numeric subset |
| Citation correctness | 95% or higher | Answered questions |
| Correct refusal on unanswerable questions | 80% or higher | 30 unanswerable questions |
| Photo query Recall@5 | 60% or higher | 40 photo queries |
| End-to-end latency, p95 | 8 seconds or less | Deployed demo |
| Cost per query | USD 0.02 or less | Deployed demo |

## 3. Users and use cases

Primary user: a repair technician or mechanic. Secondary: owners doing their own
maintenance, and trainees.

| Use case | Example input | Expected output |
| --- | --- | --- |
| Look up a specification | "Torque for the cylinder head bolts" | The value with units, the tightening sequence if given, and the source page |
| Decode an error code | "E24" | The meaning, listed causes, check procedure, and the source page |
| Find a procedure | "How do I replace the drain pump?" | Numbered steps from the manual, with the exploded-view page shown |
| Read a diagram | "Which wire goes to the ignition coil?" | The answer with the wiring diagram page displayed |
| Identify a part from a photo | Photo of a component | Likely part name, the diagram page where it appears, related procedures |
| Ask something not covered | A question about a model not in the corpus | A clear refusal saying the manuals do not cover it |

## 4. Scope of v1

Two equipment categories (home appliances and motorcycles), 20 to 30 manuals in total, roughly 3,000 to 5,000 pages, English.

**In scope:** offline indexing of PDFs as page images; text, error-code and photo
queries through one web interface; answers with page citations and the source
page displayed; filtering by manual or model; an evaluation harness and an OCR
baseline; a deployed public website.

**Out of scope (v2 candidates):** Urdu or other non-English manuals; multi-turn
diagnostic conversations; highlighting the answer region on the page; uploading
a user's own manual at query time; voice input.

## 5. Functional requirements

P0 = needed for a working demo, P1 = full v1, P2 = only if time allows.

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-1 | Convert each PDF page to an image and store it with manual, model and page-number metadata | P0 |
| FR-2 | Embed every page image with a late-interaction vision model and store the multivectors | P0 |
| FR-3 | Return the top-k pages for a text query using late-interaction scoring | P0 |
| FR-4 | Send the top pages as images to a vision LLM and return an answer | P0 |
| FR-5 | Every answer cites manual name and page number, and the UI shows the cited page | P0 |
| FR-6 | Refuse when retrieval scores are below a threshold or the LLM finds no support on the pages | P0 |
| FR-7 | Extract page text and build a BM25 keyword index for error codes and part numbers | P1 |
| FR-8 | Route each query as text, error code or photo, and merge visual and keyword results with reciprocal rank fusion | P1 |
| FR-9 | Accept a photo, have a vision LLM describe the part, and search with that description | P1 |
| FR-10 | Filter retrieval by manual or model | P1 |
| FR-11 | Log every query with retrieved pages, scores, latency, tokens and cost | P1 |
| FR-12 | Run the full gold test set from one command and write a results report | P1 |
| FR-13 | Crop figures from pages, embed them with an image model, and match photos to figures directly (stretch goal) | P2 |
| FR-14 | Rerank the top 20 pages with a vision LLM before answering | P2 |
| FR-15 | Compress the index with quantization and report the accuracy and storage trade-off | P2 |

## 6. System architecture

An offline indexing pipeline runs once per manual; a query path runs on every
question; two stores join them.

```text
INDEXING (once per manual)
  Manual PDFs
    -> render every page to an image and extract its text (PyMuPDF)
    -> embed each page image into patch vectors (ColQwen)
         |                                   |
         v                                   v
STORES
  Search indexes                        Page store
    Qdrant: one multivector per page      page images with manual,
    BM25: keywords for codes and parts    model and page number
         |                                   |
         v                                   v
QUERY TIME
  Query router  ->  Retriever  ------------> Answer model
  (text, code       (searches both           (vision LLM reads the top 3
   or photo;         indexes, merges          page images, answers with
   photos are        rankings with RRF)       a page citation)
   described by
   a vision LLM)
```

**Query flow**

1. The router classifies the input as a text question, an error code or a photo. Photos are first described by a vision LLM.
2. The retriever embeds the query, runs late-interaction search in Qdrant and BM25 keyword search, and merges both rankings with reciprocal rank fusion.
3. If the best score is below the refusal threshold, the system says the manuals do not cover the question.
4. Otherwise the top 3 page images go to the answer model with an instruction to answer only from those pages and cite manual and page.
5. The API returns the answer, citations and timing; the UI shows the cited page beside the answer.

**Design decisions**

- Pages are the retrieval unit, not text chunks, so layout, tables and drawings stay intact.
- Keyword search runs alongside visual search because error codes and part numbers need exact matching.
- The LLM client is provider-agnostic so two answer models can be compared without code changes.
- The OCR baseline shares the same API and evaluation harness, so comparisons are like for like.

## 7. Tech stack

| Layer | Choice | Reason |
| --- | --- | --- |
| Language and tooling | Python 3.11, uv, ruff, pytest | Standard for AI services |
| PDF to image | PyMuPDF, Pillow | Rendering and embedded-text extraction in one library |
| Deep learning | PyTorch, Hugging Face Transformers | Runs and loads the retrieval model |
| Page retrieval model | ColQwen2 or ColQwen2.5 via colpali-engine | Widely used, permissive licence, runs on a free Colab GPU at this corpus size |
| Vector database | Qdrant (local Docker, then Qdrant Cloud free tier) | Native multivector and MaxSim support, built-in quantization |
| Keyword search | BM25 (rank-bm25 or Qdrant sparse vectors) | Exact match for error codes and part numbers |
| Baseline pipeline | OCR (Tesseract or PaddleOCR), chunking, sentence-transformers | The comparison that proves the visual approach |
| Answer model | A vision LLM through an API, behind a provider-agnostic interface | Compare two models without code changes |
| Numerics and data | NumPy, pandas | Hand-written exercises, metrics, results tables |
| Backend | FastAPI, Pydantic, Uvicorn | Typed API, automatic docs |
| Frontend | Next.js with React, TypeScript and Tailwind CSS | Deploys natively to Vercel; product-quality interface |
| Tracing | Langfuse or Arize Phoenix | Per-query traces with cost and latency |
| Containers | Docker, Docker Compose | One command to start the system locally |
| CI | GitHub Actions: lint, tests, 20-question smoke evaluation | Regression gate |
| GPU compute | Google Colab or Kaggle | One-off page embedding job |

**Deployment**

| Piece | Where it runs | Why |
| --- | --- | --- |
| Website (Next.js) | Vercel | Free tier is enough |
| Python API and ColQwen query encoder | Hugging Face Spaces or Modal | The model needs PyTorch and several GB of memory, which does not fit Vercel serverless functions |
| Vector index | Qdrant Cloud | Managed, free tier |
| Answer model | Vision LLM provider's API | Called from the Python API |

The website calls the Python API over HTTPS; the API calls Qdrant Cloud and the LLM provider.

**Model note.** ColQwen is the starting point because it is the best-documented
option, not the top scorer. Newer models (NVIDIA Nemotron ColEmbed V2, the EVIE
family) rank higher on the ViDoRe V3 benchmark; swapping one in is experiment E3.
Check the current leaderboard before choosing.

**Storage note.** Late interaction stores about 1,000 vectors per page, so 5,000
pages is about 5 million vectors of 128 dimensions. That fits a free tier with
quantization, which is why FR-15 exists.

References:
- https://mixpeek.com/curated-lists/best-visual-document-retrieval-models
- https://arxiv.org/html/2602.03992v1 (Nemotron ColEmbed V2)
- https://qdrant.tech/documentation/tutorials-search-engineering/pdf-retrieval-at-scale/index.md
- https://qdrant.tech/blog/qdrant-colpali/
- https://arxiv.org/html/2407.01449v5 (ColPali)

## 8. Data plan

**Corpus**

- Two categories with dense diagrams and tables: home appliances (washing machines, air conditioners, refrigerators) and motorcycles, roughly half the manuals each. The `category` column in the manifest records which is which.
- Manuals only from manufacturer websites or other official sources.
- PDFs stay out of Git. Commit `data/manifest.csv` (manual_id, title, brand, model, category, source_url, downloaded_on) and the download script.
- The renderer records per page whether it has a text layer or is a scan, since this affects the OCR baseline.

**Gold test set.** Each item: question, correct manual and page numbers, reference
answer, question type. Write questions from the pages, then rephrase so they do
not copy the manual's wording. Stored in `data/gold/questions.jsonl`.

| Question type | Count | Example |
| --- | --- | --- |
| Plain text | 40 | "How often should the filter be cleaned?" |
| Table lookup | 50 | "What is the refrigerant charge for the 1.5 ton model?" |
| Diagram or exploded view | 50 | "Which part sits between the drum and the rear bearing?" |
| Error code | 30 | "What does error F21 mean?" |
| Unanswerable | 30 | A question about a model that is not in the corpus |
| Photo query | 40 | A photo of a part, taken by Zain or from a source that permits reuse |

**Splits.** Hold out 50 of the 200 text questions as a final test set; tune
thresholds and prompts only on the other 150.

## 9. Evaluation plan

Every change is judged on the gold test set against the OCR baseline, broken down by question type and by equipment category.

**Principles**

- **Evaluation comes first.** The harness and first 50 questions exist by week 2, before the main system. After that, no change is kept unless it was run as a measured experiment.
- **Three levels.** Retrieval alone (did the right page come back), answers given the retrieved pages (is the value correct and cited), and end to end (latency, cost, refusals). This shows whether a wrong answer came from search or from the LLM.
- **Error analysis.** After every full run, read 20 failures by hand and label each: wrong page retrieved, right page but misread, value in a diagram the model missed, ambiguous question, or wrong refusal. The counts decide what to build next.
- **Confidence intervals.** With 200 questions a 2 to 3 point difference can be noise. Report a bootstrap 95% interval beside every headline metric.
- **Regression gate.** CI runs the 20-question smoke set on every push and fails if Recall@5 drops by more than 5 points from the last committed result.

**Metrics**

- Retrieval: Recall@1, Recall@5, nDCG@10 at page level.
- Answer quality: exact match on numeric values and codes; an LLM judge for procedural questions, spot-checked by hand on 30 items.
- Grounding: share of answers whose cited page contains the stated value.
- Refusal: share of unanswerable questions refused, and share of answerable questions wrongly refused.
- Operations: p50 and p95 latency, cost per query, index size per page.

**Experiments**

| ID | Question | Compared |
| --- | --- | --- |
| E1 | Does visual retrieval beat OCR? | OCR and dense text baseline versus ColQwen pages |
| E2 | Does keyword search help exact codes? | Visual only versus visual plus BM25 fusion |
| E3 | Does a newer retriever help? | ColQwen2 versus one newer ViDoRe V3 leaderboard model |
| E4 | What does compression cost? | Full precision versus scalar versus binary quantization |
| E5 | Does reranking help? | Top 5 direct versus top 20 reranked by a vision LLM |
| E6 | Which photo approach works? | Describe-then-search versus figure-crop matching |
| E7 | Where is the refusal threshold? | Sweep of score thresholds against both refusal rates |

**Reporting.** Each experiment produces one row in a results table in the README
and a file in `eval/reports/`, with configuration, metrics and commit hash.

## 10. Non-functional requirements

| Area | Requirement |
| --- | --- |
| Latency | Retrieval under 1 second; full answer under 8 seconds at p95; answer text streamed to the UI |
| Cost | USD 0.02 or less per query; at most 3 page images sent to the answer model; cache repeated queries |
| Safety | Every numeric value appears with its cited page; a visible notice tells the user to confirm against the manual before acting; refusals are explicit |
| Reliability | Timeouts and one retry on LLM calls; a clear error message when a provider is down |
| Reproducibility | Pinned dependencies; one command to rebuild the index; one command to run the evaluation; fixed random seeds |
| Observability | Trace per query with retrieved pages, scores, prompt, token counts, latency and cost |
| Security | API keys in environment variables only; uploaded photos size-limited, type-checked and deleted after the request; rate limiting on the public demo; CORS restricted to the website's domain |
| Portability | Backend and Qdrant start with `docker compose up` |

## 11. Implementation plan

Eight weeks at roughly 15 to 20 hours a week.

| Week | Milestone | Deliverables | Exit criterion |
| --- | --- | --- | --- |
| 1 | M1 Foundations and data | Repository scaffold, Docker Compose with Qdrant, manifest and download script, pages rendered to images with metadata | 3,000 or more page images on disk with a complete manifest |
| 2 | M2 OCR baseline | Text extraction, chunking, dense text index, simple retrieval script, first 50 gold questions | Baseline Recall@5 measured on 50 questions |
| 3 | M3 Visual retrieval | ColQwen embedding job, Qdrant multivector collection, text-to-page search (FR-1 to FR-3) | Visual Recall@5 measured on the same 50 questions |
| 4 | M4 Gold set and harness | Full 200-question set, evaluation command, per-type breakdown, E1 written up (FR-12) | E1 results table committed |
| 5 | M5 Answers and hybrid search | Vision LLM answering, citations, refusal, BM25 index, router and fusion, FastAPI endpoints (FR-4 to FR-8, FR-10) | Numeric exact match and citation correctness measured; E2 and E7 done |
| 6 | M6 Photo queries and UI | Describe-then-search path, 40 photo queries, Next.js interface with page viewer (FR-9) | Photo Recall@5 measured; end-to-end demo works locally |
| 7 | M7 Optimisation and observability | Tracing, cost and latency logging, quantization, reranking, retriever comparison (FR-11, FR-14, FR-15) | E3, E4, E5 results committed; p95 latency and cost per query reported |
| 8 | M8 Ship | Deployment (Vercel, API host, Qdrant Cloud), CI, README with architecture and results, 3-minute demo video, short blog post | Public website works and the README reports every success metric |

The Next.js frontend adds about a week of effort for someone new to React, so
FR-13 (figure-crop matching) is a stretch goal. If time runs short, cut in this
order: FR-13, FR-14, experiment E3, the blog post. Never cut the baseline or the
gold test set, because the comparison is the result.

## 12. Learning plan

The project is built in a teach-then-build loop so that Zain can explain,
implement and measure every component by week 8.

**How each milestone runs**

1. Concept brief: the idea and the problem it solves, with a small worked example.
2. Predict: Zain writes down what he expects the metric to do before running anything.
3. Build: Zain writes the core logic from a skeleton, with review and hints. Boilerplate (Docker, config, CI) and most of the frontend can be supplied.
4. Measure: run the evaluation and compare with the prediction.
5. Error analysis: label 20 failures by cause.
6. Log: half a page in `docs/learning-log.md`.

| Week | Concepts | Implemented by hand first | Interview question |
| --- | --- | --- | --- |
| 1 | PDF internals (embedded text versus scans), rendering resolution, metadata design, Docker, what a vector database stores | A page renderer with metadata | Why does text chunking break tables and diagrams? |
| 2 | OCR, chunking strategies, dense embeddings, cosine similarity, approximate nearest-neighbour search (HNSW), Recall@k and nDCG | Recall@k and nDCG in NumPy | How do you evaluate a retriever? |
| 3 | Vision transformers and image patches, ColBERT-style late interaction, MaxSim, multivector storage | MaxSim scoring in NumPy on small arrays, before using Qdrant | What are the trade-offs of single-vector versus multi-vector retrieval? |
| 4 | Test set design, leakage, held-out splits, bootstrap confidence intervals, LLM-as-judge and its pitfalls | A bootstrap confidence interval | How do you know an improvement is real? |
| 5 | Prompting vision LLMs, grounding and citations, refusal thresholds, BM25, reciprocal rank fusion, API design | BM25 scoring and rank fusion | How do you reduce hallucination in a RAG system? |
| 6 | Image queries, image embedding models, query rewriting, React and calling an API from the browser | The photo description prompt and its evaluation | How would you support search by image? |
| 7 | Scalar and binary quantization, rescoring, reranking, tracing, latency and cost budgets | Binary quantization with Hamming distance | How do you cut vector storage cost without losing accuracy? |
| 8 | Containers, CI, deployment, writing up results | The results write-up | Walk me through your system design and where it fails. |

Hand-written versions are 20 to 50 lines each and live in `notebooks/`.
Production code then uses the library equivalents.

## 13. Repository structure and API

```text
manuallens/
  README.md
  pyproject.toml
  docker-compose.yml
  .env.example
  data/
    manifest.csv            # manual metadata and source URLs (PDFs are not committed)
    gold/questions.jsonl    # gold test set
    gold/photos/            # photo queries
  docs/
    PRD.md
    working-agreement.md    # how the project is built and its current status
    learning-log.md
  notebooks/                # hand-written exercises
  src/assistant/
    config.py               # settings from environment variables
    ingest/
      download.py           # fetch manuals listed in the manifest
      render.py             # PDF pages to images and text
      embed.py              # ColQwen page embeddings
      index.py              # write to Qdrant and BM25
    retrieve/
      visual.py             # late-interaction search
      keyword.py            # BM25 search
      fusion.py             # reciprocal rank fusion
      router.py             # query classification
      photo.py              # photo description and figure matching
    generate/
      llm.py                # provider-agnostic vision LLM client
      answer.py             # prompt, citation and refusal logic
    baseline/
      ocr_rag.py            # OCR text pipeline for comparison
    api/
      main.py               # FastAPI app
      schemas.py            # request and response models
  web/                      # Next.js frontend, deployed to Vercel
  eval/
    run_eval.py             # one-command evaluation
    metrics.py
    reports/                # results per experiment
  tests/
  .github/workflows/ci.yml
```

**API contract**

| Endpoint | Input | Output |
| --- | --- | --- |
| `POST /query` | `question` (text) or `image` (file), optional `manual_id`, optional `top_k` | `answer`, `refused` (boolean), `citations` (manual, page, score), `latency_ms`, `cost_usd` |
| `GET /pages/{manual_id}/{page}` | Path parameters | The page image |
| `GET /manuals` | None | List of manuals with model and page count |
| `GET /health` | None | Service and index status |

**Website:** a query box with photo upload, the answer with its citations, and a
viewer showing the cited source page.

## 14. Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Manuals are copyrighted and cannot be redistributed | Repository or demo taken down | Officially published manuals only; commit the manifest and scripts, not the PDFs; show single pages with a link to the source |
| No local GPU for embedding | Indexing blocked | Embed on a free Colab or Kaggle GPU as a one-off batch job and upload vectors to Qdrant |
| Query-time embedding needs the model loaded | Demo hosting cost | Host the query encoder on a free GPU Space, or run it on CPU and measure the latency |
| Index too large for the free tier | Hosting cost | Quantization (FR-15); reduce the corpus to 3,000 pages if needed |
| Wrong torque or clearance value is trusted | Equipment damage or injury | Mandatory citation with the page displayed, a refusal threshold, a visible confirm-against-manual notice |
| Photo queries perform poorly | A headline feature underdelivers | Report the result honestly; keep describe-then-search as the default; treat figure matching as an experiment |
| Gold set written by one person is biased | Inflated metrics | Rephrase questions away from manual wording; hold out 50 questions; ask one other person to contribute 20 |
| LLM API costs during evaluation | Budget overrun | Cache responses; run the full set only at milestones; smoke set in CI |
| Frontend takes longer than planned | Schedule slips | Most frontend code is supplied as boilerplate; FR-13 is a stretch goal |
| Scope creep | Project never ships | P0 and P1 only until week 6; follow the cut order |

## 15. Open decisions

- [x] Equipment category: both home appliances and motorcycles.
- [ ] Vision LLM provider for answers. Recommended: whichever API Zain already has credit for.
- [x] Where embedding runs: local 8 GB GPU, with Colab or Kaggle as the fallback.
- [x] Weekly time budget and start date: 15 to 20 hours a week from 13 November 2026.
- [x] Project and repository name: ManualLens (`manuallens`).
