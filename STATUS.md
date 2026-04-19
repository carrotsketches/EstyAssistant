# Project Status

## Completed Phases

### Phase 1: Backend API
- FastAPI app with Mangum Lambda adapter
- `POST /process` — CV pipeline via S3 (bytes I/O)
- `GET /upload-url` — presigned S3 URLs for direct browser upload
- `POST /listing/generate` — Claude Vision metadata generation
- S3 helpers, Pydantic models, Dockerfile
- **PR #2** — merged

### Phase 2: Frontend Shell
- Next.js (App Router) with Tailwind CSS
- Drag-and-drop upload with S3 presigned URLs
- Print size selector (5x7, 8x10, 11x14, 16x20)
- Before/after image preview with download links
- Typed API client
- **PR #2** — merged

### Phase 3: AI Metadata + Listing Editor
- `POST /mockups/generate` endpoint with S3 storage
- ListingEditor component: editable title, tag chips, description
- MockupGallery component: frame mockup previews with skeleton loading
- Bytes-based mockup generation in shared core
- **PR #4** — merged

### Phase 4: Etsy Integration
- Web-based OAuth 2.0 PKCE flow (replaces CLI local server)
- DynamoDB credential store for tokens + job tracking
- `POST /publish` — process + create Etsy draft + upload files
- `GET /jobs/{id}` — poll async job status
- Connect/disconnect UI with status indicator
- Publish section with price input and polling spinner
- OAuth callback page
- Auto-save to history on successful publish
- **PR #5** — merged

### Phase 5: Infrastructure & Deployment
- SAM template: Lambda (container), S3, DynamoDB, API Gateway
- `scripts/deploy-backend.sh` — one-command backend deploy
- `DEPLOY.md` — step-by-step guide from AWS account creation to running app
- Vercel config for frontend deployment
- GitHub Actions CI: core tests, backend tests, frontend build
- **PR #3** — merged

### Listing History
- DynamoDB storage for saved listings
- Backend CRUD: `GET/POST /listings`, `GET/DELETE /listings/{id}`
- Frontend: collapsible history panel, save button, load into editor
- **PR #6** — merged

### UI Polish
- Toast notification system (success/error/info with auto-dismiss)
- Mobile-responsive layout throughout
- Batch upload: multi-file select, sequential processing, progress indicator
- Loading skeletons and spinner animations
- **PR #7** — merged

### Custom Templates + Dark Mode + CI
- Custom frame template upload via UI (DynamoDB + S3)
- Template manager: list bundled + custom, upload, delete
- Dark mode toggle with system preference detection
- GitHub Actions CI: 3 jobs (core tests, backend tests, frontend build)
- **PR #8** — open

## Test Coverage

| Suite | Tests | Location |
|-------|-------|----------|
| Core pipeline + CV steps | 87 | `tests/` |
| Backend API routes | 85 | `backend/tests/` |
| Frontend | Builds clean | `frontend/` |
| **Total** | **172** | |

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `GET` | `/upload-url` | Presigned S3 upload URL |
| `POST` | `/process` | Run CV pipeline |
| `POST` | `/listing/generate` | AI metadata via Claude Vision |
| `POST` | `/mockups/generate` | Frame mockup compositing |
| `GET` | `/auth/etsy/start` | Begin Etsy OAuth |
| `POST` | `/auth/etsy/callback` | Exchange OAuth code |
| `GET` | `/auth/etsy/status` | Check Etsy connection |
| `POST` | `/auth/etsy/disconnect` | Disconnect Etsy |
| `POST` | `/publish` | Process + create Etsy draft |
| `GET` | `/jobs/{id}` | Poll job status |
| `GET` | `/listings` | List saved listings |
| `POST` | `/listings` | Save listing to history |
| `GET` | `/listings/{id}` | Get a saved listing |
| `DELETE` | `/listings/{id}` | Delete a saved listing |
| `GET` | `/templates` | List frame templates |
| `POST` | `/templates` | Save custom template |
| `POST` | `/templates/upload` | Get template upload URL |
| `DELETE` | `/templates/{id}` | Delete custom template |

## Estimated Costs

| Service | Monthly Cost |
|---------|-------------|
| AWS Lambda + API Gateway | ~$0 (free tier) |
| S3 | ~$0.50 |
| DynamoDB | ~$0 (free tier) |
| Vercel | $0 (hobby) |
| Anthropic API | ~$0.05-0.10/image |
| **Total** | **~$1-5/month** |

## Current Deployment

- **Frontend**: Live at `https://esty-assistant.vercel.app/` (Vercel Hobby, free)
  - Deployed from fork: `carrotsketches/EstyAssistant`
  - Auto-deploys on push to `main` branch of the fork
  - Sync fork from `paleyzpl/EstyAssistant` to trigger redeploy
- **Backend**: Not deployed yet (frontend is static/UI-only)
- **Development repo**: `paleyzpl/EstyAssistant` (Claude Code has access here)

## Next Steps (Priority Order)

### 1. Deploy Backend to Fly.io (Free Tier) — ~15 min
Everything is ready in the repo:
- `backend/Dockerfile.fly` — Python 3.12 slim image for Fly.io
- `fly.toml` — Fly.io config (auto-stop, 512MB, shared CPU)
- `scripts/setup-free.sh` — One-command setup script

Steps:
1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Sign up: `fly auth signup` (use new ProtonMail)
3. Run: `bash scripts/setup-free.sh`
4. Set secrets: `fly secrets set ANTHROPIC_API_KEY=... ETSY_API_KEY=...`
5. Update Vercel env var `NEXT_PUBLIC_API_URL` to the Fly.io URL

### 2. Set Up Supabase (Free Tier) — ~10 min
For database (credentials, jobs, listings) and S3-compatible storage:
1. Sign up at supabase.com (use new ProtonMail)
2. Create project, get connection string + S3 endpoint
3. Set env vars on Fly.io: `DB_BACKEND=supabase`, `STORAGE_BACKEND=supabase`

### 3. Connect Etsy OAuth
1. Create Etsy app at developers.etsy.com
2. Set callback URL to `https://esty-assistant.vercel.app/auth/etsy/callback`
3. Add `ETSY_API_KEY` to Fly.io secrets

### 4. Future Enhancements
- [ ] Custom domain for Vercel
- [ ] Analytics dashboard — track listing performance
- [ ] Watermark option for preview images
- [ ] SEO score improvements
- [ ] Bundle generator refinements
