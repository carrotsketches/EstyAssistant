# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Etsy Assistant is a tool for pen & ink sketch artists (the shop is "Carrot Sketches") that processes sketch photos into print-ready digital downloads and generates optimized Etsy listing metadata via Claude Vision.

Two interfaces share the same core library:
- **CLI** — Click-based command-line tool (`uv run etsy-assistant`)
- **Web** — Next.js frontend (Vercel) + FastAPI backend (AWS Lambda container)

## Architecture

```
CLI:  etsy-assistant process sketch.jpg -s 8x10
Web:  [Browser] → [Next.js on Vercel] → [API Gateway] → [FastAPI on Lambda] → [S3]
                                                                              → [Claude API]
                                                                              → [Etsy API]
Both use: src/etsy_assistant/ (shared core package)
```

### Shared Core Package (`src/etsy_assistant/`)

The image processing, listing generation, bundle/mockup logic, and Etsy integration live in `src/etsy_assistant/`. Both the CLI and web backend import from this package.

- **Do not duplicate** this package into `backend/src/`. The backend imports it via `PYTHONPATH=../src:src`.
- The Dockerfile copies from `src/etsy_assistant/` at the **repo root** — builds must run from there, not from `backend/`.

### Backend (`backend/src/api/`)

FastAPI app wrapped with Mangum for Lambda. `main.py` wires CORS, a per-IP in-memory rate limiter (`RATE_LIMIT_PER_MINUTE`, default 60; resets on cold start), and routers from `routes/`. The Lambda entry point is `handler = Mangum(app, lifespan="off")`.

#### Persistence (`api/credentials.py`)

Single DynamoDB-backed module for Etsy tokens, OAuth state, async jobs, saved listings, and custom templates. Uses `boto3.resource("dynamodb")` against `DYNAMODB_TABLE` (default `etsy-assistant-credentials`). Item keys follow the pattern `pk = "<kind>#<id>"` (e.g. `listing#abc123`, `job#xyz`), with a single `etsy_credentials` row for the connected Etsy account.

### Frontend (`frontend/src/`)

Next.js App Router. `app/page.tsx` is the main upload/process/publish surface. Components live in `src/components/` (ListingEditor, MockupGallery, ListingHistory, TemplateManager, BundleGenerator, AnalyticsDashboard, SeoScore, ImageCompare, Toast, DarkModeToggle, KeyboardShortcuts). `src/lib/api.ts` is the typed backend client. OAuth callback lives at `app/auth/etsy/callback/`.

**Important** (from `frontend/AGENTS.md`): the Next.js version in this repo has breaking changes from training data. Read `node_modules/next/dist/docs/` before writing framework code; heed deprecation notices.

## Image Processing Pipeline

**Step order**: `autocrop → perspective → background → contrast` (defined by `STEP_ORDER` in `pipeline.py`).

Each step is a pure function `(np.ndarray, PipelineConfig) → np.ndarray`. Steps can be skipped individually; the pipeline **continues on step failure** (exceptions are logged and the previous result is used).

Two I/O modes in `pipeline.py`:
- `process_image_bytes(bytes, sizes, ...)` → `list[(size_label, png_bytes)]` — used by the web API
- `process_image(path, output_path, sizes, ...)` → `list[Path]` — used by the CLI; supports `debug=True` to dump intermediates to `<input>/debug/`

Additional standalone step modules under `steps/`: `resize.py`, `output.py` (file + bytes encoding), `keywords.py` (Claude Vision listing metadata), `mockup.py` (frame compositing, bundled templates in `templates/templates.json`), `watermark.py`.

Bundle logic lives in `bundles.py`: `BUNDLE_SIZES` (3-pack 75%, 5-pack 70% of sum), `merge_tags`, `calculate_bundle_price`, `generate_bundle_title`, `generate_bundle_description_simple`, plus a Claude-driven grouping prompt.

## Development Setup

Requires Python 3.12+, uv, Node.js 22+.

### Core / CLI
```bash
uv sync --group dev                         # Install deps
uv run etsy-assistant --help                # CLI commands: process, batch, info, generate-listing, batch-listing, publish
uv run pytest                               # Run all core tests
uv run pytest tests/test_pipeline.py        # Run one file
uv run pytest -k "perspective"              # Run by keyword
uv run pytest -v tests/test_autocrop.py::test_autocrop_finds_paper  # Single test
```

### Backend
```bash
cd backend
uv sync --group dev
PYTHONPATH=../src:src uvicorn api.main:app --reload   # Local server on :8000
PYTHONPATH=../src:src uv run pytest                   # All backend tests
PYTHONPATH=../src:src uv run pytest tests/test_process.py -v
```

Backend tests mock AWS with `moto[dynamodb,s3]`; no real AWS or Anthropic credentials are needed.

### Frontend
```bash
cd frontend
npm install
npm run dev       # Dev server on :3000
npm run build     # Production build (also serves as type check)
npm run lint      # ESLint
```

## Environment Variables

Backend (`backend/.env`):
- `S3_BUCKET` — image storage bucket
- `AWS_REGION` — default `us-east-1`
- `CORS_ORIGINS` — comma-separated allowed origins
- `RATE_LIMIT_PER_MINUTE` — default 60
- `ANTHROPIC_API_KEY` — Claude Vision
- `ETSY_API_KEY` — Etsy OAuth client ID (PKCE flow, no client secret needed)
- `FRONTEND_URL` — OAuth callback redirect (default `http://localhost:3000`)
- `DYNAMODB_TABLE` — table name (default `etsy-assistant-credentials`)

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — backend URL (default `http://localhost:8000`)

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check (skipped by rate limiter) |
| `GET` | `/upload-url` | Presigned S3 upload URL (browser uploads directly to S3) |
| `POST` | `/process` | Run CV pipeline on an uploaded image |
| `POST` | `/listing/generate` | AI metadata via Claude Vision |
| `POST` | `/mockups/generate` | Frame mockup compositing |
| `GET`/`POST`/`DELETE` | `/templates[/…]` | List bundled + custom templates, upload custom, delete |
| `POST` | `/bundles/generate` | Generate N-pack bundle listings from individual listings |
| `GET` | `/analytics` | Aggregate views/favorites for connected shop's listings |
| `GET` | `/auth/etsy/start` | Begin Etsy OAuth, return redirect URL |
| `POST` | `/auth/etsy/callback` | Exchange OAuth code for tokens |
| `GET` | `/auth/etsy/status` | Check if Etsy is connected |
| `POST` | `/auth/etsy/disconnect` | Disconnect Etsy account |
| `POST` | `/publish` | Process + create Etsy draft listing (async job) |
| `GET` | `/jobs/{id}` | Poll async job status |
| `GET`/`POST` | `/listings` | List / save listings (history) |
| `GET`/`DELETE` | `/listings/{id}` | Fetch / delete saved listing |

## Key Constraints

- CV operations use OpenCV (`cv2`) with **BGR** color order; images are `np.ndarray` throughout (not PIL).
- Listing titles: max 140 chars. Tags: max 13 items, each ≤20 chars.
- Etsy digital file upload limit: 20 MB.
- Supported print sizes: `5x7`, `8x10`, `11x14`, `16x20`, `A4`. Default DPI: 300.
- Browser uploads go **directly to S3** via presigned URLs — not through the API.
- `backend/Dockerfile` must be built from the **repo root** to access `src/etsy_assistant/`.

## Testing

Tests use synthetic images (numpy arrays) from `tests/conftest.py` — no real image files or AWS/Anthropic credentials needed. Backend tests stub AWS with moto.

```bash
uv run pytest                                      # Core (with coverage, fails <90%)
cd backend && PYTHONPATH=../src:src uv run pytest   # Backend (with coverage, fails <90%)
cd frontend && npm run build                        # Frontend type check + build
```

**Coverage floor: 90%.** Both Python suites run `pytest-cov` with `--cov-fail-under=90` pinned in `pyproject.toml`. Any new code must keep the suite at or above 90% or add tests to get there — do not merge with coverage regressions. The only paths currently exempted via `# pragma: no cover` are genuinely interactive flows (e.g. `etsy_api.authorize()`, which spins up a local `HTTPServer` and opens a browser).

## CI (`.github/workflows/`)

- `ci.yml` — runs on every push/PR to `main`: three parallel jobs (core tests, backend tests, frontend build).
- `deploy.yml` — manual `workflow_dispatch`; uses OIDC (`AWS_ROLE_ARN` var) to run `sam build && sam deploy` with secrets/vars for CORS, frontend URL, alarm email, and API keys.

## Deployment

**Stack: AWS end-to-end.** Backend on Lambda (container) behind API Gateway, S3 for images, DynamoDB for state. Frontend static on Vercel. `infra/template.yaml` is the source of truth for all AWS resources. There is no non-AWS path — do not add Fly.io, Supabase, or other provider shims.

| Service | Purpose |
|---------|---------|
| Lambda (container) | FastAPI app via Mangum adapter |
| API Gateway (HTTP API) | Public HTTPS endpoint, CORS, routes `/*` → Lambda |
| ECR | Stores the Lambda container image |
| S3 | Uploaded sketches, processed outputs, mockups, custom templates |
| DynamoDB | Single table for credentials, jobs, listings, templates |
| IAM | Lambda execution role (S3 + DynamoDB + logs) |
| CloudWatch Logs | Lambda logs + metrics |
| SSM Parameter Store | `ANTHROPIC_API_KEY`, `ETSY_API_KEY` |

### Deploy commands
```bash
# SAM (preferred — provisions everything)
cd infra && sam build && sam deploy --guided

# One-shot helper
scripts/deploy-backend.sh

# Manual docker build for local container testing
docker build -f backend/Dockerfile -t etsy-assistant .
```

For the end-to-end rollout plan (AWS account → SAM → SSM secrets → Vercel env → Etsy OAuth app → hardening) see `DEPLOY.md` and `STATUS.md`.

## Dependencies

- **Core**: opencv-python-headless, Pillow, numpy, click, anthropic, httpx
- **Backend (additional)**: fastapi, mangum, boto3, uvicorn
- **Backend dev**: pytest, moto[dynamodb,s3], httpx
- **Frontend**: next, react, tailwindcss, typescript
