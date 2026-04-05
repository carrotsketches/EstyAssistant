# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Etsy Assistant is a web application for pen & ink sketch artists that processes sketch photos into print-ready digital downloads and generates optimized Etsy listing metadata using Claude Vision. The shop is "Carrot Sketches."

The app has two main parts:
- **Frontend**: Next.js (App Router) on Vercel — upload UI, before/after preview, size selector
- **Backend**: FastAPI on AWS Lambda (container image) — image processing pipeline, AI metadata, S3 storage

## Architecture

```
[Browser] → [Next.js on Vercel] → [API Gateway] → [FastAPI on Lambda] → [S3 / DynamoDB]
                                                                        → [Claude API]
                                                                        → [Etsy API]
```

## Development Setup

### Backend

```bash
cd backend
uv sync --group dev          # Install dependencies
PYTHONPATH=src uvicorn api.main:app --reload  # Run locally on :8000
uv run pytest                # Run tests
```

Requires: Python 3.12+, uv

### Frontend

```bash
cd frontend
npm install                  # Install dependencies
npm run dev                  # Run locally on :3000
npm run build                # Production build
```

Requires: Node.js 22+

### Environment Variables

Backend (`backend/.env`):
- `S3_BUCKET` — S3 bucket name for image storage
- `AWS_REGION` — AWS region (default: us-east-1)
- `CORS_ORIGINS` — Comma-separated allowed origins
- `ANTHROPIC_API_KEY` — For Claude Vision listing generation

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — Backend URL (default: http://localhost:8000)

## Project Structure

```
EstyAssistant/
├── backend/                           # FastAPI app → Lambda container
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── etsy_assistant/            # Core image processing package
│   │   │   ├── config.py              # PipelineConfig frozen dataclass
│   │   │   ├── pipeline.py            # CV pipeline orchestration
│   │   │   ├── etsy_api.py            # Etsy OAuth + API integration
│   │   │   ├── steps/                 # Pipeline steps (pure functions)
│   │   │   │   ├── autocrop.py        # Crop to paper region
│   │   │   │   ├── perspective.py     # Perspective/rotation correction
│   │   │   │   ├── background.py      # Paper background cleanup
│   │   │   │   ├── contrast.py        # Ink contrast enhancement
│   │   │   │   ├── resize.py          # Print size scaling
│   │   │   │   ├── output.py          # Image encoding (bytes + file)
│   │   │   │   ├── keywords.py        # Claude Vision metadata generation
│   │   │   │   └── mockup.py          # Frame template compositing
│   │   │   └── templates/             # Frame mockup images + JSON
│   │   └── api/                       # FastAPI web layer
│   │       ├── main.py                # App + Mangum Lambda handler
│   │       ├── models.py              # Pydantic request/response schemas
│   │       ├── s3.py                  # S3 presigned URL helpers
│   │       └── routes/
│   │           ├── upload.py          # GET /upload-url
│   │           ├── process.py         # POST /process
│   │           └── listing.py         # POST /listing/generate
│   └── tests/
├── frontend/                          # Next.js app → Vercel
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Main upload + process page
│   │   │   └── layout.tsx
│   │   └── lib/
│   │       └── api.ts                 # Typed backend API client
│   ├── package.json
│   └── next.config.ts
├── infra/
│   └── template.yaml                 # SAM template (Lambda + S3 + DynamoDB)
├── src/                               # Original CLI package (preserved)
├── tests/                             # Original CLI tests
└── pyproject.toml                     # Original CLI config
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/upload-url` | Presigned S3 upload URL |
| `POST` | `/process` | Run CV pipeline on uploaded image |
| `POST` | `/listing/generate` | AI metadata via Claude Vision |

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

## Deployment

### Backend (AWS Lambda container)
```bash
cd infra
sam build
sam deploy --guided
```

### Frontend (Vercel)
Connect the `frontend/` directory to Vercel. Set `NEXT_PUBLIC_API_URL` to the API Gateway URL from SAM output.

## Testing

Backend tests use synthetic images (numpy arrays) via fixtures in `conftest.py`. No real image files or AWS credentials needed for unit tests.

```bash
cd backend && uv run pytest           # Backend tests
cd frontend && npm run build           # Frontend type check + build
```

## Dependencies

**Backend**: opencv-python-headless, Pillow, numpy, anthropic, httpx, fastapi, mangum, boto3

**Frontend**: next, react, tailwindcss, typescript
