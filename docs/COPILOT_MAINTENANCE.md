# How to maintain this project with limited AI assistance

> **Audience:** a developer (you, a teammate, or GitHub Copilot in agent mode)
> making *small, scoped* edits to Etsy Assistant — bug fixes, copy tweaks,
> small refactors, dependency bumps. Larger features should still go through
> a human-driven design pass.

This document is the contract between you and the codebase: do these things
and you can ship without breaking anything.

If anything here disagrees with [`/CLAUDE.md`](../CLAUDE.md), CLAUDE.md wins —
it has the authoritative architecture rules. This file is the *workflow*
guide.

---

## The 30-second loop (read this first)

```bash
# 1. Make your change.
# 2. Run the relevant test suite (PICK the one that touches your change):

# Core library / CLI:
uv run pytest

# Backend API:
cd backend && PYTHONPATH=../src:src uv run pytest

# Frontend:
cd frontend && npm run build && npm run lint

# 3. If tests fail, read the failure, fix the code (not the test, unless the
#    test is asserting wrong behavior), and re-run. Iterate until green.
# 4. Commit with a single-line message describing the WHY.
```

That's the whole loop. The rest of this document is *why* it works and the
guard rails that keep it working.

---

## Repo cheat sheet

| You changed…                       | Run this test suite                     | Coverage floor |
|-----------------------------------|------------------------------------------|----------------|
| `src/etsy_assistant/**`           | `uv run pytest` (from repo root)         | 80%            |
| `backend/src/api/**`              | `cd backend && PYTHONPATH=../src:src uv run pytest` | 80% |
| `frontend/src/**`                 | `cd frontend && npm run build && npm run lint` | n/a (typecheck only) |
| `infra/template.yaml`             | nothing automated — `sam validate infra/template.yaml` |
| `.github/workflows/*.yml`         | `actionlint` (CI runs the workflow on push) |
| `pyproject.toml` deps             | both Python suites                       |                |

The `--cov-fail-under=80` flag is **pinned** in both `pyproject.toml`s. A test
suite that drops below 80% line coverage fails — which means *adding code
without adding tests* is rejected by the suite, not just by review.

---

## Where things live

```
src/etsy_assistant/        ← shared core library (used by CLI + backend)
  pipeline.py              ← orchestrates the CV steps
  steps/                   ← one file per step (autocrop, perspective, …)
  bundles.py               ← 3-pack / 5-pack listing generator
  etsy_api.py              ← Etsy OAuth + REST client
  cli.py                   ← Click commands (`etsy-assistant ...`)
backend/src/api/           ← FastAPI app (Lambda)
  main.py                  ← app factory, CORS, rate limit, router includes
  routes/                  ← one file per HTTP route group
  credentials.py           ← DynamoDB-backed state (creds, jobs, listings, templates)
  s3.py                    ← presigned URLs + read/write helpers
frontend/src/              ← Next.js App Router
  app/page.tsx             ← main UI
  components/              ← React components
  lib/api.ts               ← typed backend client
tests/                     ← core library tests
backend/tests/             ← backend tests (mock AWS via moto)
docs/TRACEABILITY.md       ← feature → test matrix (read before editing)
docs/COPILOT_MAINTENANCE.md← this file
CLAUDE.md                  ← architecture / deploy / constraints
DEPLOY.md                  ← end-to-end rollout plan
```

Before changing a file, **open `docs/TRACEABILITY.md`** and find the row for
your feature. It tells you which tests must stay green and where there are
known gaps.

---

## The autonomous loop (for Copilot agent mode)

When you ask Copilot (or any agent) to make a change, give it this exact
prompt structure. The "keep iterating until tests pass" instruction is the
critical bit — without it, agents tend to declare victory the moment the
code compiles.

```
Make this change: <describe the change>.

Acceptance:
1. The change does X / fixes Y.
2. Both Python test suites pass:
     uv run pytest
     cd backend && PYTHONPATH=../src:src uv run pytest
3. If you touched frontend code, also:
     cd frontend && npm run build
4. Coverage stays ≥ 80% on both Python suites (the suites enforce this
   themselves; if you add code, add tests).
5. Do NOT skip or weaken any existing test to make the suite pass — fix
   the code instead.

Run the relevant test command after every edit. Keep editing and re-running
until 100% of tests pass. If a test you didn't touch starts failing, that's
a regression — fix it. Only stop when both suites are fully green.

Commit each logical change as a single git commit. Do not push until I
review the diff.
```

For Copilot specifically: enable "auto-iterate on test failures" and point
it at the test commands above. The 80% coverage floor will block the agent
from merging untested new code.

---

## Common edits and how to handle them

### "Tweak a CV step" (e.g. autocrop sensitivity)

1. Edit the function in `src/etsy_assistant/steps/<step>.py`.
2. Run `uv run pytest tests/test_<step>.py -v`.
3. Run the full pipeline test: `uv run pytest tests/test_pipeline.py -v`.
4. If you changed output values (not behavior), update the assertions in the
   step's test file with the new expected numbers — but include a comment
   explaining *why* the number changed.

### "Add a field to a listing JSON"

1. Update `src/etsy_assistant/steps/keywords.py::ListingMetadata`.
2. Update `save_metadata` / `load_metadata` to roundtrip the new field.
3. Run `uv run pytest tests/test_keywords.py`.
4. Update `backend/src/api/models.py::ListingMetadataResponse` to expose it.
5. Update `frontend/src/lib/api.ts` (the TypeScript interface).
6. Surface in `frontend/src/components/ListingEditor.tsx` if user-editable.
7. Run all three test suites (core, backend, `npm run build`).

### "Change a backend route response"

1. Edit `backend/src/api/routes/<route>.py` and the matching pydantic model
   in `backend/src/api/models.py`.
2. Update the test in `backend/tests/test_<route>.py` (the route tests
   assert on the response body — they will catch you).
3. Update `frontend/src/lib/api.ts` so the TS type stays accurate.
4. `cd frontend && npm run build` — TypeScript will catch consumer breakage.

### "Bump a dependency"

1. Python:
   ```bash
   uv sync --upgrade-package <name>
   uv run pytest
   cd backend && uv sync --upgrade-package <name> && PYTHONPATH=../src:src uv run pytest
   ```
2. Frontend:
   ```bash
   cd frontend && npm update <name> && npm run build && npm run lint
   ```
3. Read the package's CHANGELOG. Pay attention to the Next.js note in
   `frontend/AGENTS.md` — Next has had breaking changes from training data.

### "Fix a flaky deployment"

`infra/template.yaml` is the source of truth. Don't add ad-hoc resources
elsewhere. After editing, validate locally:

```bash
cd infra && sam validate
cd infra && sam build
```

A real deploy goes through the manual `Deploy Backend` GitHub Action — see
`CLAUDE.md` § Quick Deploy.

---

## Manual smoke tests (when there are no automated ones)

The matrix in `docs/TRACEABILITY.md` flags rows as **GAP — manual smoke**.
Here are the manual checks for each:

### Frontend (no unit tests yet)
```bash
cd frontend && npm run dev
```
Then in a browser at `http://localhost:3000`:
1. Upload a sketch JPG.
2. Click "Process" — confirm preview shows.
3. Click "Generate Listing" — confirm title/tags/description appear.
4. Click "Generate Mockups" — confirm at least one frame mockup renders.
5. Open dark mode toggle, listing history, template manager — each should
   open without console errors.
6. Open the browser DevTools Network tab and confirm `NEXT_PUBLIC_API_URL`
   is being hit (not localhost when deployed).

### CLI `auth` command (uses real browser)
```bash
uv run etsy-assistant auth --api-key $ETSY_API_KEY --port 5556
```
You should: see browser open, complete Etsy authorization, see "Authenticated
as user N" + "Credentials saved to …" in the terminal. There is no automated
test for this — it has to be a real browser.

### CORS
Hit the backend with a non-allowed origin and confirm the CORS preflight
fails:
```bash
curl -i -X OPTIONS https://<api>/health \
  -H "Origin: https://evil.example.com" \
  -H "Access-Control-Request-Method: GET"
```
Expect missing `Access-Control-Allow-Origin` header.

---

## What NOT to do

- **Don't lower the 80% coverage floor.** It exists so untested changes get
  rejected automatically. If a legitimate change pushes coverage below 80%,
  add tests; don't relax the floor.
- **Don't add new test-skipping markers** (`@pytest.mark.skip`, `xfail`) to
  make a failing test pass. If the test was right, the code is wrong.
- **Don't duplicate `src/etsy_assistant/` into `backend/src/`.** Both the
  CLI and backend share the same package via `PYTHONPATH=../src:src`. See
  CLAUDE.md § "Shared Core Package".
- **Don't add framework abstractions** "for the future." Three similar lines
  is fine. Premature abstraction has burned us before.
- **Don't write to `git push --force` on `main`** or skip pre-commit hooks.
- **Don't commit `.env` files or anything containing API keys.** SSM
  Parameter Store + GitHub Secrets are the only legitimate places for them.

---

## When automated tests aren't enough

Most of the matrix is well-covered, but the following changes always need a
human eye:

| Type of change                       | Why automated tests can't catch it |
|--------------------------------------|------------------------------------|
| Visual regressions in the frontend   | No screenshot tests yet            |
| Etsy API contract changes            | We mock Etsy; we don't talk to it  |
| Claude prompt quality                | Output is non-deterministic        |
| Lambda cold-start latency            | Not exercised by `TestClient`     |
| OAuth flow with a real browser       | `authorize()` opens a browser      |
| Real S3 / DynamoDB I/O               | Tests use moto                     |
| Production CORS configuration        | Only verified at deploy time       |

For these, run the manual smoke tests above and watch the deployed app for
10 minutes after release. CloudWatch alarms (`ALARM_EMAIL` in the deploy
workflow) will email you on Lambda errors.

---

## Quick links

- Architecture & constraints: [`CLAUDE.md`](../CLAUDE.md)
- Deploy plan & status:        [`DEPLOY.md`](../DEPLOY.md), [`STATUS.md`](../STATUS.md)
- Feature ↔ test matrix:       [`docs/TRACEABILITY.md`](TRACEABILITY.md)
- Frontend-specific notes:     [`frontend/AGENTS.md`](../frontend/AGENTS.md)
