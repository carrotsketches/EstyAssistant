# Feature → Test Traceability Matrix

This document maps every shipped feature in the Etsy Assistant repo to the test
files and test cases that exercise it. It exists so a maintainer (human or AI,
e.g. GitHub Copilot) can quickly answer two questions before changing code:

1. **What tests must I keep green?** Find your feature row, look at "Tests".
2. **Where are the gaps?** Rows tagged **GAP** have weak or no automated coverage —
   exercise extra care, write a test before you change the code, or rely on
   manual verification.

Generated 2026-04-27 against branch `claude/ai-maintenance-prep-v5r6K`.

Baseline test counts: **160 core / 123 backend tests passing**.
Baseline coverage: **86.91% core / 94.92% backend**.

---

## How to read this matrix

| Column      | Meaning                                                            |
|-------------|--------------------------------------------------------------------|
| Feature     | A behavior or surface area the user / API consumer relies on.      |
| Source      | Primary file(s) implementing the feature.                          |
| Tests       | Test files / classes that exercise it.                             |
| Coverage    | Approximate line coverage from `pytest-cov` (see Notes for misses).|
| Status      | ✅ well-covered, ⚠️ partial, **GAP** = needs new tests.             |

When `Tests` lists a class (`TestX`), it means every method of that class.

---

## 1. Core image-processing pipeline (`src/etsy_assistant/`)

### 1.1 Top-level pipeline

| Feature                                   | Source              | Tests                                             | Coverage | Status |
|-------------------------------------------|---------------------|---------------------------------------------------|----------|--------|
| File-based pipeline (`process_image`)     | pipeline.py         | tests/test_pipeline.py (5 tests)                  | 94%      | ✅     |
| Bytes-based pipeline (`process_image_bytes`) | pipeline.py      | tests/test_pipeline_bytes.py                      | 94%      | ✅     |
| Skip-step support                         | pipeline.py         | test_pipeline.py::test_pipeline_skip_steps        | 94%      | ✅     |
| Debug intermediate dump                   | pipeline.py         | test_pipeline.py::test_pipeline_debug_mode        | 94%      | ✅     |
| Bad-input error handling                  | pipeline.py         | test_pipeline.py::test_pipeline_bad_input         | 94%      | ✅     |

### 1.2 Pipeline steps

| Feature              | Source                  | Tests                                        | Coverage | Status |
|----------------------|-------------------------|----------------------------------------------|----------|--------|
| Autocrop             | steps/autocrop.py       | tests/test_autocrop.py                       | 100%     | ✅     |
| Perspective correct  | steps/perspective.py    | test_perspective.py + test_perspective_deskew.py | 95%   | ✅     |
| Background cleanup   | steps/background.py     | tests/test_background.py                     | 100%     | ✅     |
| Contrast enhance     | steps/contrast.py       | tests/test_contrast.py                       | 100%     | ✅     |
| Resize for print     | steps/resize.py         | tests/test_resize.py (6 tests, all sizes)    | 97%      | ✅     |
| Encode/save output   | steps/output.py         | tests/test_output_bytes.py                   | 100%     | ✅     |
| Watermark            | steps/watermark.py      | tests/test_watermark.py                      | 94%      | ✅     |

### 1.3 AI metadata (Claude Vision)

| Feature                         | Source                  | Tests                       | Coverage | Status |
|---------------------------------|-------------------------|-----------------------------|----------|--------|
| Image encoding (file + bytes)   | steps/keywords.py       | TestEncodeImage             | 98%      | ✅     |
| Claude response parsing         | steps/keywords.py       | TestParseResponse           | 98%      | ✅     |
| `generate_listing` from path    | steps/keywords.py       | TestGenerateListing         | 98%      | ✅     |
| `generate_listing_from_bytes`   | steps/keywords.py       | TestGenerateListingFromBytes| 98%      | ✅     |
| Save / load metadata sidecar    | steps/keywords.py       | TestSaveMetadata, TestLoadMetadata | 98% | ✅     |

### 1.4 Frame mockups

| Feature                               | Source              | Tests                       | Coverage | Status |
|---------------------------------------|---------------------|-----------------------------|----------|--------|
| List bundled templates                | steps/mockup.py     | test_mockup_files.py        | 94%      | ✅     |
| Frame interior detection              | steps/mockup.py     | test_mockup_files.py        | 94%      | ✅     |
| Single-template mockup (file & bytes) | steps/mockup.py     | test_mockup_files.py + test_mockup_bytes.py | 94% | ✅     |
| All-template mockup (file & bytes)    | steps/mockup.py     | test_mockup_files.py + test_mockup_bytes.py | 94% | ✅     |
| Orientation detection                 | steps/mockup.py     | test_mockup_files.py + test_mockup_bytes.py | 94% | ✅     |

### 1.5 Bundle generator

| Feature                          | Source        | Tests                                          | Coverage | Status |
|----------------------------------|---------------|------------------------------------------------|----------|--------|
| Load listing JSONs               | bundles.py    | TestLoadListingJsons                           | 78%      | ✅     |
| Load Etsy CSV export             | bundles.py    | TestLoadEtsyCsv                                | 78%      | ✅     |
| Tag-overlap grouping (fallback)  | bundles.py    | TestGroupByTags                                | 78%      | ✅     |
| **AI grouping (`group_with_ai`)**| bundles.py    | tests/test_bundles_ai.py::TestGroupWithAi      | 78%      | ✅ (new) |
| **Manual config grouping**       | bundles.py    | tests/test_bundles_ai.py::TestGroupFromConfig  | 78%      | ✅ (new) |
| Tag merging                      | bundles.py    | TestMergeTags                                  | 78%      | ✅     |
| Bundle title / price             | bundles.py    | TestGenerateBundleTitle, TestCalculateBundlePrice | 78%   | ✅     |
| Simple bundle description        | bundles.py    | TestGenerateBundleDescriptionSimple            | 78%      | ✅     |
| **AI bundle description**        | bundles.py    | tests/test_bundles_ai.py::TestGenerateBundleDescriptionAi | 78% | ✅ (new) |
| End-to-end `generate_bundles`    | bundles.py    | TestGenerateBundles + tests/test_bundles_ai.py | 78%      | ✅     |

### 1.6 Etsy API client

| Feature                              | Source        | Tests                                  | Coverage | Status |
|--------------------------------------|---------------|----------------------------------------|----------|--------|
| Credentials save / load (file)       | etsy_api.py   | TestEtsyCredentials                    | 79%      | ✅     |
| PKCE generator                       | etsy_api.py   | TestPKCE                               | 79%      | ✅     |
| OAuth `authorize` (CLI, browser)     | etsy_api.py   | _none — opens a real browser_          | 79%      | **GAP — manual** |
| Web-flow `build_auth_url` / `exchange_code` | etsy_api.py | tests/test_etsy_api_web.py        | 79%      | ✅     |
| Refresh access token                 | etsy_api.py   | TestRefreshToken                       | 79%      | ✅     |
| Auto-refresh on 401                  | etsy_api.py   | tests/test_etsy_api_web.py             | 79%      | ✅     |
| Create draft listing                 | etsy_api.py   | TestCreateDraftListing                 | 79%      | ✅     |
| Upload listing image (file + bytes)  | etsy_api.py   | TestUploadListingImage + web tests     | 79%      | ✅     |
| Upload listing file (file + bytes)   | etsy_api.py   | TestUploadListingFile + web tests      | 79%      | ✅     |
| 20MB digital file size limit         | etsy_api.py   | test_rejects_large_file                | 79%      | ✅     |

> **Note on 79%:** the missing lines are all inside `authorize()` (lines 82-176) —
> the desktop OAuth flow that spins up a local HTTP server and opens a browser.
> Testing this end-to-end requires a real browser, so it's covered by manual
> smoke-tests, not unit tests. When editing this function, run the CLI:
> `uv run etsy-assistant auth --api-key $ETSY_API_KEY` and complete the flow.

### 1.7 CLI (`etsy_assistant.cli`)

| Command            | Source     | Tests                                          | Status |
|--------------------|------------|------------------------------------------------|--------|
| `--help` / `--version` | cli.py | TestMainGroup                                  | ✅     |
| `info`             | cli.py     | TestInfoCommand                                | ✅     |
| `process`          | cli.py     | TestProcessCommand (4 tests)                   | ✅     |
| `batch`            | cli.py     | TestBatchCommand                               | ✅     |
| `generate-listing` | cli.py     | TestGenerateListingCommand                     | ✅     |
| `batch-listing`    | cli.py     | TestBatchListingCommand                        | ✅     |
| `generate-bundles` | cli.py     | TestGenerateBundlesCommand                     | ✅     |
| `auth`             | cli.py     | tests/test_cli.py::TestAuthCommand (new)       | ✅ (new) |
| `publish` (dry-run)| cli.py     | TestPublishCommand::test_dry_run_skips_upload  | ✅     |
| `publish` (live)   | cli.py     | tests/test_cli.py::TestPublishCommand (new full path) | ✅ (new) |

---

## 2. Backend (`backend/src/api/`)

### 2.1 Infrastructure

| Feature                | Source         | Tests                                 | Coverage | Status |
|------------------------|----------------|---------------------------------------|----------|--------|
| `/health`              | main.py        | TestHealthEndpoint                    | 98%      | ✅     |
| Per-IP rate limiter    | main.py        | tests/test_rate_limit.py              | 98%      | ✅     |
| CORS headers           | main.py        | _implicit via test client_            | 98%      | ⚠️ (no explicit test) |

### 2.2 Storage helpers

| Feature                       | Source              | Tests                       | Coverage | Status |
|-------------------------------|---------------------|-----------------------------|----------|--------|
| Presigned S3 upload URL       | s3.py               | tests/test_s3_helpers.py    | 100%     | ✅     |
| Read / write S3 image         | s3.py               | tests/test_s3_helpers.py    | 100%     | ✅     |
| DynamoDB credentials CRUD     | credentials.py      | TestCredentials             | 100%     | ✅     |
| OAuth state save / consume    | credentials.py      | TestOAuthState              | 100%     | ✅     |
| Async job state               | credentials.py      | TestJobs                    | 100%     | ✅     |
| Listing history CRUD          | credentials.py      | TestListings                | 100%     | ✅     |
| Custom-template metadata CRUD | credentials.py      | TestCustomTemplates         | 100%     | ✅     |

### 2.3 Routes

| Method  | Path                        | Source                | Tests                             | Coverage | Status |
|---------|-----------------------------|-----------------------|-----------------------------------|----------|--------|
| GET     | `/upload-url`               | routes/upload.py      | TestUploadUrlEndpoint             | 100%     | ✅     |
| POST    | `/process`                  | routes/process.py     | TestProcessEndpoint               | 93%      | ✅     |
| POST    | `/listing/generate`         | routes/listing.py     | TestListingGenerateEndpoint       | 100%     | ✅     |
| POST    | `/mockups/generate`         | routes/mockups.py     | TestMockupsEndpoint               | 93%      | ✅     |
| GET     | `/auth/etsy/start`          | routes/auth.py        | TestAuthStart                     | 94%      | ✅     |
| POST    | `/auth/etsy/callback`       | routes/auth.py        | TestAuthCallback                  | 94%      | ✅     |
| GET     | `/auth/etsy/status`         | routes/auth.py        | TestAuthStatus                    | 94%      | ✅     |
| POST    | `/auth/etsy/disconnect`     | routes/auth.py        | TestAuthDisconnect                | 94%      | ✅     |
| POST    | `/auth/etsy/callback` exchange-code error | routes/auth.py | tests/test_templates_api.py + auth_publish (new) | 94% | ✅ (new) |
| POST    | `/publish`                  | routes/publish.py     | TestPublish                       | 91%      | ✅     |
| GET     | `/jobs/{id}`                | routes/publish.py     | TestJobStatus                     | 91%      | ✅     |
| POST    | `/publish/bulk`             | routes/publish.py     | tests/test_bulk_publish.py        | 91%      | ✅     |
| Token-refresh callback (`_on_token_refresh`) | routes/publish.py | tests/test_publish_extra.py (new) | 91% | ✅ (new) |
| Publish error path (DDB job marked failed)   | routes/publish.py | tests/test_publish_extra.py (new) | 91% | ✅ (new) |
| GET     | `/listings`                 | routes/listings.py    | TestListListings                  | 100%     | ✅     |
| GET     | `/listings/{id}`            | routes/listings.py    | TestGetListing                    | 100%     | ✅     |
| POST    | `/listings`                 | routes/listings.py    | TestSaveListing                   | 100%     | ✅     |
| DELETE  | `/listings/{id}`            | routes/listings.py    | TestDeleteListing                 | 100%     | ✅     |
| **GET** | `/templates`                | routes/templates.py   | tests/test_templates_api.py (new) | 69 → 100%| ✅ (new) |
| **POST**| `/templates/upload`         | routes/templates.py   | tests/test_templates_api.py (new) | 69 → 100%| ✅ (new) |
| **POST**| `/templates`                | routes/templates.py   | tests/test_templates_api.py (new) | 69 → 100%| ✅ (new) |
| **DELETE** | `/templates/{id}`        | routes/templates.py   | tests/test_templates_api.py (new) | 69 → 100%| ✅ (new) |
| POST    | `/bundles/generate`         | routes/bundles.py     | tests/test_bundles_api.py         | 98%      | ✅     |
| GET     | `/analytics`                | routes/analytics.py   | tests/test_analytics.py           | 95%      | ✅     |

---

## 3. Frontend (`frontend/src/`)

| Surface                          | Source                                    | Tests | Status |
|----------------------------------|-------------------------------------------|-------|--------|
| Upload / process / publish flow  | app/page.tsx                              | none  | **GAP — manual smoke** |
| Listing editor                   | components/ListingEditor.tsx              | none  | **GAP — manual smoke** |
| Mockup gallery                   | components/MockupGallery.tsx              | none  | **GAP — manual smoke** |
| Listing history                  | components/ListingHistory.tsx             | none  | **GAP — manual smoke** |
| Template manager                 | components/TemplateManager.tsx            | none  | **GAP — manual smoke** |
| Bundle generator                 | components/BundleGenerator.tsx            | none  | **GAP — manual smoke** |
| Analytics dashboard              | components/AnalyticsDashboard.tsx         | none  | **GAP — manual smoke** |
| Etsy OAuth callback page         | app/auth/etsy/callback/                   | none  | **GAP — manual smoke** |
| Typed API client                 | lib/api.ts                                | none  | **GAP — typecheck only** |

`npm run build` is the only automated check on the frontend (it doubles as a
type-check). For UI behavior we rely on manual verification — see
`docs/COPILOT_MAINTENANCE.md` § "Manual smoke tests".

---

## 4. Cross-cutting concerns

| Concern                          | How it's verified                              |
|----------------------------------|------------------------------------------------|
| 80% coverage floor (Python)      | `pytest-cov --cov-fail-under=80` in both `pyproject.toml`s |
| AWS interactions                 | `moto[dynamodb,s3]` mocks; no real AWS in tests |
| Anthropic API                    | `unittest.mock.patch` on `anthropic.Anthropic` |
| Etsy API (httpx)                 | `unittest.mock.patch` on `httpx.Client` or `_request_with_refresh` |
| Browser-based OAuth (`authorize`)| **Manual** — there is no automated test for this |
| Lambda cold-start / Mangum       | Not tested directly; `/health` round-trips via `TestClient` |

---

## 5. Where to add tests next

Listed in priority order if you want to push coverage higher:

1. **Frontend unit tests.** `frontend/` has zero unit tests. Adding Vitest +
   React Testing Library for `ListingEditor`, `BundleGenerator`, and `lib/api.ts`
   would close the largest hole in the matrix.
2. **CORS headers** — assert that an `Origin: <allowed>` request gets
   `Access-Control-Allow-Origin` back; today this is only verified by the
   browser at runtime.
3. **CLI `auth` command failure paths** — what happens when `authorize` raises?
   Currently only the success path is tested.
4. **Keywords pipeline retry / rate-limit handling** — Claude API rate limits
   aren't exercised in tests.

These are *nice-to-have*, not blocking. The matrix above is green enough that
small Copilot edits should be safe as long as the autonomous loop in
`COPILOT_MAINTENANCE.md` is followed.
