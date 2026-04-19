# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Etsy Assistant is a tool for pen & ink sketch artists that processes sketch photos into print-ready digital downloads and generates optimized Etsy listing metadata using Claude Vision. The shop is "Carrot Sketches."

It supports two interfaces sharing the same core library:
- **CLI**: Click-based command-line tool (`uv run etsy-assistant`)
- **Web**: Next.js frontend (Vercel) + FastAPI backend (AWS Lambda container)

## Architecture

```
CLI:  etsy-assistant process sketch.jpg -s 8x10
Web:  [Browser] → [Next.js on Vercel] → [API Gateway] → [FastAPI on Lambda] → [S3]
                                                                              → [Claude API]
Both use: src/etsy_assistant/ (shared core package)
```

## Shared Core Package (`src/etsy_assistant/`)

The core image processing and Etsy integration code lives in `src/etsy_assistant/`. Both the CLI and web backend import from this package.

- **Do not duplicate** this package into `backend/src/`. The backend imports it via `PYTHONPATH`.
- The Dockerfile copies from `src/etsy_assistant/` at the repo root.

## Development Setup

### CLI

```bash
uv sync --group dev                  # Install all dependencies
uv run etsy-assistant --help         # Run the CLI
uv run pytest                        # Run core tests
```

### Backend (web API)

```bash
cd backend
uv sync --group dev                                    # Install dependencies
PYTHONPATH=../src:src uvicorn api.main:app --reload     # Run locally on :8000
PYTHONPATH=../src:src uv run pytest                     # Run tests
```

### Frontend

```bash
cd frontend
npm install                  # Install dependencies
npm run dev                  # Run locally on :3000
npm run build                # Production build
```

Requires: Python 3.12+, uv, Node.js 22+

### Environment Variables

Backend (`backend/.env`):
- `S3_BUCKET` — S3 bucket name for image storage
- `AWS_REGION` — AWS region (default: us-east-1)
- `CORS_ORIGINS` — Comma-separated allowed origins
- `ANTHROPIC_API_KEY` — For Claude Vision listing generation
- `ETSY_API_KEY` — Etsy OAuth client ID
- `FRONTEND_URL` — Frontend URL for OAuth callback (default: http://localhost:3000)
- `DYNAMODB_TABLE` — DynamoDB table for credentials + jobs

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — Backend URL (default: http://localhost:8000)

## Project Structure

```
EstyAssistant/
├── src/etsy_assistant/                # SHARED core package (CLI + web)
│   ├── config.py                      # PipelineConfig frozen dataclass
│   ├── pipeline.py                    # CV pipeline (file + bytes I/O)
│   ├── cli.py                         # Click CLI commands
│   ├── etsy_api.py                    # Etsy OAuth + API integration
│   └── steps/                         # Pipeline steps (pure functions)
│       ├── autocrop.py                # Crop to paper region
│       ├── perspective.py             # Perspective/rotation correction
│       ├── background.py              # Paper background cleanup
│       ├── contrast.py                # Ink contrast enhancement
│       ├── resize.py                  # Print size scaling
│       ├── output.py                  # Image encoding (bytes + file)
│       ├── keywords.py                # Claude Vision metadata generation
│       └── mockup.py                  # Frame template compositing
├── tests/                             # Core package tests
├── pyproject.toml                     # CLI project config
│
├── backend/                           # FastAPI web layer → Lambda container
│   ├── Dockerfile                     # Built from repo root
│   ├── pyproject.toml                 # Web-only dependencies
│   ├── src/api/                       # FastAPI routes + helpers
│   │   ├── main.py                    # App + Mangum Lambda handler
│   │   ├── models.py                  # Pydantic request/response schemas
│   │   ├── s3.py                      # S3 presigned URL helpers
│   │   ├── credentials.py             # DynamoDB credential + job store
│   │   └── routes/
│   │       ├── upload.py              # GET /upload-url
│   │       ├── process.py             # POST /process
│   │       ├── listing.py             # POST /listing/generate
│   │       ├── mockups.py             # POST /mockups/generate
│   │       ├── auth.py                # Etsy OAuth endpoints
│   │       └── publish.py             # POST /publish, GET /jobs/{id}
│   └── tests/                         # API + integration tests
│
├── frontend/                          # Next.js app → Vercel
│   ├── src/app/page.tsx               # Main upload + process + publish page
│   ├── src/app/auth/etsy/callback/    # OAuth callback page
│   ├── src/components/                # ListingEditor, MockupGallery
│   └── src/lib/api.ts                 # Typed backend API client
│
└── infra/template.yaml                # SAM template (Lambda + S3 + DynamoDB)
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/upload-url` | Presigned S3 upload URL |
| `POST` | `/process` | Run CV pipeline on uploaded image |
| `POST` | `/listing/generate` | AI metadata via Claude Vision |
| `POST` | `/mockups/generate` | Frame mockup compositing |
| `GET` | `/auth/etsy/start` | Begin Etsy OAuth, return redirect URL |
| `POST` | `/auth/etsy/callback` | Exchange OAuth code for tokens |
| `GET` | `/auth/etsy/status` | Check if Etsy is connected |
| `POST` | `/auth/etsy/disconnect` | Disconnect Etsy account |
| `POST` | `/publish` | Process + create Etsy draft listing |
| `GET` | `/jobs/{id}` | Poll async job status |
| `GET` | `/listings` | List saved listings (history) |
| `GET` | `/listings/{id}` | Get a single saved listing |
| `POST` | `/listings` | Save a listing to history |
| `DELETE` | `/listings/{id}` | Delete a saved listing |

## Image Processing Pipeline

**Step order**: `autocrop → perspective → background → contrast`

Each step is a pure function: `(np.ndarray, PipelineConfig) → np.ndarray`. Steps can be skipped. The pipeline continues on step failure.

Two I/O modes:
- `process_image_bytes()` — bytes in, list of `(size, bytes)` out (for web API)
- `process_image()` — file path in, file paths out (for CLI)

## Key Constraints

- All CV operations use OpenCV (`cv2`) with BGR color order
- Images flow through the pipeline as `np.ndarray` (not PIL)
- Listing titles max 140 chars, tags max 13 items each max 20 chars
- Etsy digital file upload limit is 20 MB
- Supported print sizes: 5x7, 8x10, 11x14, 16x20, A4
- Default output DPI is 300
- Browser uploads directly to S3 via presigned URLs (not through the API)
- The Dockerfile must be built from the **repo root** (not `backend/`) to access `src/`

## Deployment

**Target stack: AWS end-to-end.** The backend runs on AWS Lambda (container image) behind API Gateway, with S3 for image storage and DynamoDB for credentials, jobs, listings, and custom templates. The frontend is static and deployed to Vercel, but all backend state lives in AWS. Fly.io and Supabase are **not** used — do not add code, config, or docs that reference them.

### AWS Services

| Service | Purpose |
|---------|---------|
| Lambda (container) | FastAPI app via Mangum adapter |
| API Gateway (HTTP API) | Public HTTPS endpoint, CORS, routes `/*` → Lambda |
| ECR | Stores the Lambda container image |
| S3 | Uploaded sketches, processed outputs, mockups, custom templates |
| DynamoDB | Single table for Etsy credentials, async jobs, saved listings, templates |
| IAM | Lambda execution role (S3 + DynamoDB access, logs) |
| CloudWatch Logs | Lambda logs + metrics |
| SSM Parameter Store (or Secrets Manager) | `ANTHROPIC_API_KEY`, `ETSY_API_KEY`, `ETSY_CLIENT_SECRET` |

### Backend (AWS Lambda container)
```bash
# Build from repo root
docker build -f backend/Dockerfile -t etsy-assistant .

# Or via SAM (preferred — provisions Lambda + API Gateway + S3 + DynamoDB)
cd infra && sam build && sam deploy --guided
```

`infra/template.yaml` is the source of truth for all AWS resources.

### Frontend (Vercel)
Connect the `frontend/` directory to Vercel. Set `NEXT_PUBLIC_API_URL` to the API Gateway invoke URL from the SAM stack outputs.

### Deployment Plan (AWS)

**Phase A — First backend deploy**
1. Create AWS account and IAM user with `AdministratorAccess` for bootstrap; configure `aws configure` locally.
2. Install SAM CLI and Docker.
3. `cd infra && sam build && sam deploy --guided` — accept defaults, pick a stack name (e.g. `etsy-assistant-prod`) and region (`us-east-1`).
4. Capture stack outputs: `ApiUrl`, `S3Bucket`, `DynamoDBTable`.
5. Set Lambda env vars (via SAM template parameters or console): `S3_BUCKET`, `DYNAMODB_TABLE`, `CORS_ORIGINS`, `FRONTEND_URL`.
6. Store secrets in SSM Parameter Store (`/etsy-assistant/anthropic-api-key`, `/etsy-assistant/etsy-api-key`, `/etsy-assistant/etsy-client-secret`) and reference them from `template.yaml`.

**Phase B — Wire frontend to AWS**
1. In Vercel project settings, set `NEXT_PUBLIC_API_URL` to the API Gateway URL.
2. Redeploy frontend; verify `/health` from the browser.
3. Add the Vercel domain to `CORS_ORIGINS` on the Lambda.

**Phase C — Etsy OAuth**
1. Register the app at developers.etsy.com; set callback to `https://<vercel-domain>/auth/etsy/callback`.
2. Put `ETSY_API_KEY` and `ETSY_CLIENT_SECRET` in SSM; redeploy the stack.
3. End-to-end test: connect Etsy → process a sketch → publish a draft listing.

**Phase D — Hardening**
- CloudWatch alarms on Lambda errors + 5xx from API Gateway.
- S3 lifecycle rule: expire uploads/ prefix after 7 days.
- DynamoDB on-demand billing (default in template).
- GitHub Actions: OIDC role for `sam deploy` on push to `main`.
- Custom domain via Route 53 + ACM cert (optional).

### Estimated Cost (AWS-only)

| Service | Monthly |
|---------|---------|
| Lambda + API Gateway | ~$0 (free tier) |
| S3 | ~$0.50 |
| DynamoDB (on-demand) | ~$0 (free tier) |
| CloudWatch Logs | ~$0.10 |
| Anthropic API | ~$0.05–0.10 per image |
| Vercel (frontend) | $0 (Hobby) |
| **Total** | **~$1–5/month** at low volume |

## Testing

Tests use synthetic images (numpy arrays) via fixtures in `conftest.py`. No real image files or AWS credentials needed.

```bash
uv run pytest                                         # Core tests (from repo root)
cd backend && PYTHONPATH=../src:src uv run pytest      # Backend tests
cd frontend && npm run build                           # Frontend type check + build
```

## Dependencies

**Core**: opencv-python-headless, Pillow, numpy, click, anthropic, httpx

**Backend (additional)**: fastapi, mangum, boto3, uvicorn

**Frontend**: next, react, tailwindcss, typescript
