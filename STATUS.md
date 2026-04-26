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

Deployment target is **AWS end-to-end** (Lambda + API Gateway + S3 + DynamoDB). Fly.io and Supabase are not used. See `CLAUDE.md` → Deployment for the full plan.

### 1. Deploy Backend to AWS via SAM — ~30 min
Everything is ready in the repo:
- `backend/Dockerfile` — Lambda container (Python 3.12, built from repo root)
- `infra/template.yaml` — SAM template (Lambda + API Gateway + S3 + DynamoDB + alarms)
- `.github/workflows/deploy.yml` — OIDC-based CI deploy (preferred path)
- `scripts/deploy-backend.sh` — local fallback wrapper around `sam build && sam deploy`

Follow `infra/README.md` for the full bootstrap. TL;DR:
1. One-time: deploy `etsy-assistant-oidc` CloudFormation stack to create the GitHub OIDC provider + `etsy-assistant-deploy` role.
2. Set GitHub repo variables (`AWS_ROLE_ARN`, `CORS_ORIGINS`, `FRONTEND_URL`, `ALARM_EMAIL`) and secrets (`ANTHROPIC_API_KEY`).
3. Trigger **Actions → Deploy Backend → Run workflow**.
4. Capture stack outputs (`ApiUrl`, `BucketName`); set `NEXT_PUBLIC_API_URL` in Vercel to `ApiUrl`.

### 2. Connect Etsy OAuth
1. Create Etsy app at developers.etsy.com.
2. Set callback URL to `https://esty-assistant.vercel.app/auth/etsy/callback`.
3. Add the Vercel origin to the Lambda's `CORS_ORIGINS` and redeploy.

### 3. Harden Production
- CloudWatch alarms on Lambda errors + API Gateway 5xx.
- S3 lifecycle rule: expire `uploads/` after 7 days.
- GitHub Actions: OIDC role for `sam deploy` on push to `main` (already wired — PR #13).

### 4. Future Enhancements
- [ ] Custom domain via Route 53 + ACM (backend) and Vercel (frontend)
- [ ] Analytics dashboard — track listing performance
- [ ] Watermark option for preview images
- [ ] SEO score improvements
- [ ] Bundle generator refinements
