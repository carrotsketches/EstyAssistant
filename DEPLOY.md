# Deployment Guide

**Stack**: Vercel (frontend) + AWS Lambda (backend) + API Gateway + S3 + DynamoDB
**Cost**: ~$1-5/month after free tier (dominated by Anthropic API usage)

Two ways to deploy the backend:

- **[Path A: Local machine](#path-a-deploy-from-your-local-machine)** — run `sam deploy` yourself from a shell with AWS CLI + Docker installed.
- **[Path B: GitHub Actions](#path-b-deploy-from-github-actions-no-terminal)** — no local CLI or Docker; the workflow builds the image and runs `sam deploy` via OIDC.

Path B is easiest if you don't already have AWS/Docker set up locally.

---

## Path A: Deploy from your local machine

### Prerequisites

1. **AWS CLI v2**: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html
2. **AWS SAM CLI**: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
3. **Docker Desktop**: https://www.docker.com/products/docker-desktop/
4. **Node.js 22+**: https://nodejs.org/
5. **Git**

### Step 1: AWS account setup

1. Sign up at https://aws.amazon.com/
2. Create an IAM user `etsy-assistant-deploy` with these managed policies:
   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonAPIGatewayAdministrator`
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AWSCloudFormationFullAccess`
   - `IAMFullAccess`
3. Generate access keys for the IAM user and run `aws configure`.

### Step 2: Anthropic API key

1. https://console.anthropic.com → Create Key
2. Save as `sk-ant-...`

### Step 3: Deploy backend

```bash
git clone https://github.com/paleyzpl/EstyAssistant.git
cd EstyAssistant
export ANTHROPIC_API_KEY="sk-ant-..."
./scripts/deploy-backend.sh
```

Prints the API Gateway URL at the end.

### Step 4: Deploy frontend to Vercel

1. Go to https://vercel.com → Sign in with GitHub.
2. **Add New Project** → import your fork of the repo.
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js (auto-detected)
   - **Environment Variables**: `NEXT_PUBLIC_API_URL` = the API URL from Step 3
4. Deploy.

### Step 5: Update CORS and redeploy

```bash
export CORS_ORIGINS="https://your-app.vercel.app,http://localhost:3000"
./scripts/deploy-backend.sh
```

### Costs (AWS free tier + usage)

| Service | Free tier | After free tier |
|---------|-----------|----------------|
| Lambda | 1M requests + 400K GB-s | ~$0 at low volume |
| API Gateway | 1M calls (12 months) | ~$0 |
| S3 | 5 GB (12 months) | ~$0.50/month |
| DynamoDB | 25 GB + 25 RCU/WCU | ~$0 |
| ECR | 500 MB | ~$0 |
| Anthropic API | pay-per-use | ~$0.05-0.10/image |
| **Total** | | **$1-5/month** |

---

## Path B: Deploy from GitHub Actions (no terminal)

Same AWS stack as Path A, but the GitHub Actions runner builds the Docker image and runs `sam deploy` for you. Credentials are federated via OIDC, so no long-lived AWS access keys are stored anywhere.

### Step 1: AWS account + OIDC provider

1. Sign up at https://aws.amazon.com/ (requires name, address, credit card, phone verification)
2. Sign in to the AWS Console → **IAM** → **Identity providers** → **Add provider**
   - Provider type: **OpenID Connect**
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
   - Click **Add provider**

### Step 2: IAM role for GitHub Actions

1. IAM → **Roles** → **Create role**
2. Trusted entity type: **Web identity**
   - Identity provider: `token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
   - GitHub organization: `carrotsketches`
   - GitHub repository: `EstyAssistant`
   - (Leave branch empty to allow any branch; tighten later)
   - Note: `carrotsketches/EstyAssistant` is the fork that auto-deploys. If you also want to run the workflow from the dev repo `paleyzpl/EstyAssistant`, add a second `StringLike` entry for its `sub` to the trust policy after creation.
3. Attach permissions — pick one:
   - **Simple (recommended for a personal project):** attach `PowerUserAccess` + `IAMFullAccess`. SAM needs `IAMFullAccess` to create the Lambda execution role.
   - **Tight:** craft an inline policy covering CloudFormation, Lambda, ECR, S3, DynamoDB, API Gateway v2, SNS, CloudWatch Logs/Alarms, and `iam:*Role*` on the stack's execution role. Easier to do after the first successful deploy.
4. Name the role e.g. `GitHubActionsEtsyAssistantDeployer`
5. Copy its ARN (e.g. `arn:aws:iam::123456789012:role/GitHubActionsEtsyAssistantDeployer`) — you'll paste it into GitHub next.

### Step 3: Anthropic API key (and optional Etsy)

1. https://console.anthropic.com → Create Key → save `sk-ant-...`
2. (Optional) https://www.etsy.com/developers → create app → save keystring

### Step 4: GitHub repo configuration

In the GitHub repo → **Settings**:

**Secrets and variables → Actions → Secrets** (encrypted, never logged):
- `ANTHROPIC_API_KEY` — the `sk-ant-...` key
- `ETSY_API_KEY` — the Etsy keystring (optional; leave unset if not using publish)

**Secrets and variables → Actions → Variables** (visible in workflow logs; safe because they're not secrets):
- `AWS_ROLE_ARN` — the role ARN from Step 2
- `CORS_ORIGINS` — comma-separated, e.g. `http://localhost:3000` for first deploy
- `FRONTEND_URL` — your Vercel URL once known, or `http://localhost:3000` for first deploy
- `ALARM_EMAIL` — email for CloudWatch alarm notifications (optional; leave unset to skip)

### Step 5: First deploy

1. GitHub repo → **Actions** tab → **Deploy Backend** workflow → **Run workflow**
2. Leave the defaults (`stack_name=etsy-assistant`, `region=us-east-1`) or change them
3. When it finishes (~5 min for first deploy, ~2 min subsequent), open the final log step. The `ApiUrl` from the stack outputs is your backend URL.

### Step 6: Deploy frontend to Vercel

Same as Path A Step 4, with `NEXT_PUBLIC_API_URL` set to the `ApiUrl` from Step 5.

### Step 7: Fix CORS and redeploy

1. Back in GitHub → Settings → Variables → edit `CORS_ORIGINS` to include your Vercel URL:
   `https://your-app.vercel.app,http://localhost:3000`
2. Actions → Deploy Backend → Run workflow again. `sam deploy` picks up the new parameter and updates the Lambda env var.

### Troubleshooting

- **`Not authorized to perform sts:AssumeRoleWithWebIdentity`** — the trust policy's `sub` condition doesn't match the repo the workflow is running from. Check it reads `repo:carrotsketches/EstyAssistant:*` (or whichever repo you're deploying from).
- **`AccessDenied` during `sam deploy`** — role is missing a permission. Either attach `PowerUserAccess` + `IAMFullAccess`, or read the error to add the specific action to your inline policy.
- **First build is slow (~5 min)** — Docker layers are uncached on the runner. Subsequent deploys reuse ECR image layers.

---

## Local development

```bash
# Backend (port 8000)
cd backend
uv sync --group dev
export S3_BUCKET="your-bucket" AWS_REGION="us-east-1" ANTHROPIC_API_KEY="sk-ant-..."
PYTHONPATH=../src:src uvicorn api.main:app --reload
```

```bash
# Frontend (port 3000)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Backend tests mock AWS via `moto`, so no real AWS credentials are needed to run them.

---

## Troubleshooting

### CORS errors
- Update the `CORS_ORIGINS` variable (GitHub Actions) or env var (local) and redeploy.

### Frontend build fails on Vercel
- Make sure **Root Directory** is set to `frontend` in Vercel project settings.

---

## Tear down

```bash
aws cloudformation delete-stack --stack-name etsy-assistant --region us-east-1
aws s3 rb s3://etsy-assistant-images-ACCOUNT_ID --force
aws ecr delete-repository --repository-name etsy-assistant --force --region us-east-1
```
