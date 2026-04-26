# Deployment Guide

Deployment target is **AWS end-to-end**: Lambda (container) + API Gateway + S3 + DynamoDB, with the frontend on Vercel. Fly.io and Supabase are not used.

The detailed, copy-pasteable bootstrap lives in [`infra/README.md`](infra/README.md). This page is a high-level summary of the two paths and the tradeoffs.

| Path | Where deploys run | Local tools needed | Best for |
|------|-------------------|--------------------|----------|
| **CI (recommended)** | GitHub Actions, federated to AWS via OIDC | none | Day-to-day deploys, no local Docker/AWS CLI |
| **Local** | Your laptop | AWS CLI v2, SAM CLI, Docker | Iterating on `template.yaml` before merging |

Both paths use the same `infra/template.yaml`. Stack name defaults to `etsy-assistant`, region `us-east-1`.

## Cost

| Service | Free tier | After free tier |
|---------|-----------|----------------|
| Lambda | 1M requests + 400k GB-s/mo | ~$0 at low volume |
| API Gateway (HTTP) | 1M calls/mo (first 12 months) | ~$0 |
| S3 | 5 GB (first 12 months) | ~$0.50/mo |
| DynamoDB on-demand | 25 GB + 25 RCU/WCU | ~$0 |
| ECR | 500 MB | ~$0 |
| CloudWatch Logs | 5 GB | ~$0.10/mo |
| Vercel Hobby | unlimited personal projects | $0 |
| Anthropic API | pay-per-use | ~$0.05–0.10 / image |
| **Total** | | **~$1–5/mo** at low volume |

## CI deploy (Path 1)

End-to-end summary — see `infra/README.md` for the full walkthrough.

1. **Bootstrap** (one-time): deploy `infra/bootstrap-oidc.yaml` → creates the GitHub OIDC provider and the `etsy-assistant-deploy` role.
2. **GitHub config**: in repo settings, add variables (`AWS_ROLE_ARN`, `CORS_ORIGINS`, `FRONTEND_URL`, `ALARM_EMAIL`) and secrets (`ANTHROPIC_API_KEY`, `ETSY_API_KEY`).
3. **Deploy**: Actions → **Deploy Backend** → **Run workflow**. The job assumes the OIDC role, runs `sam build && sam deploy`, and prints stack outputs.
4. **Wire frontend**: set `NEXT_PUBLIC_API_URL` in Vercel to the `ApiUrl` output, redeploy.
5. **Fix CORS**: update the `CORS_ORIGINS` GitHub variable to include the Vercel URL, re-run the workflow.

## Local deploy (Path 2)

```bash
# Prereqs: aws CLI, sam CLI, Docker, AWS creds with admin (for first deploy)
export ANTHROPIC_API_KEY=sk-ant-...
export CORS_ORIGINS=http://localhost:3000
./scripts/deploy-backend.sh
```

The script logs in to ECR, builds the image from the repo root, and runs `sam deploy`. It prints `ApiUrl` and `BucketName` at the end.

## Etsy OAuth

After the first successful deploy:

1. Register an app at <https://developers.etsy.com>; set the callback to `https://<vercel-domain>/auth/etsy/callback`.
2. Set `ETSY_API_KEY` (and any client secret, when added) in GitHub secrets.
3. Re-run the **Deploy Backend** workflow so Lambda picks up the new env vars.

## Local development

```bash
# Backend on :8000
cd backend
uv sync --group dev
export S3_BUCKET=your-dev-bucket AWS_REGION=us-east-1 ANTHROPIC_API_KEY=sk-ant-...
PYTHONPATH=../src:src uvicorn api.main:app --reload
```

```bash
# Frontend on :3000
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Troubleshooting

- **`Not authorized to perform sts:AssumeRoleWithWebIdentity`** — the OIDC role's trust policy `sub` doesn't match the repo running the workflow. It should be `repo:carrotsketches/EstyAssistant:*`.
- **`AccessDenied` during `sam deploy`** — the deploy role lacks a permission. Easiest unblock: keep `AdministratorAccess` until the first deploy succeeds, then tighten with help from IAM Access Analyzer.
- **First build is slow (~5 min)** — Docker layers are uncached on the runner. Subsequent deploys reuse ECR layers.
- **CORS errors in the browser** — update the `CORS_ORIGINS` GitHub variable and re-run the deploy workflow; Lambda only sees the new value after redeploy.
- **Frontend build fails on Vercel** — make sure **Root Directory** is `frontend` in the Vercel project.

## Teardown

```bash
# Empty the bucket first (CloudFormation can't delete a non-empty bucket)
aws s3 rm s3://etsy-assistant-images-<account-id> --recursive
aws cloudformation delete-stack --stack-name etsy-assistant
aws ecr delete-repository --repository-name etsy-assistant --force
# Optional: also remove the OIDC bootstrap stack
aws cloudformation delete-stack --stack-name etsy-assistant-oidc
```
