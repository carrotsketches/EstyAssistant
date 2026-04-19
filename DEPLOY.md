# Deployment Guide

Three deployment paths are supported:

- **[Free & Privacy-First](#path-a-free--privacy-first)** — Fly.io + Supabase + Vercel, zero AWS, no credit card required
- **[AWS](#path-b-aws)** — Lambda + S3 + DynamoDB, deployed from your local machine
- **[AWS from GitHub Actions](#path-c-aws-from-github-actions-no-terminal)** — same AWS stack as Path B, but deployed entirely from GitHub's web UI (no local CLI, Docker, or terminal)

If you're not sure, use **Path A**. If you already know AWS and want to deploy without installing anything locally, use **Path C**.

---

## Path A: Free & Privacy-First

**Stack**: Vercel (frontend) + Fly.io (backend) + Supabase (DB + storage)
**Cost**: $0/month forever (within free tiers)
**Time**: ~25 minutes

### Step 1: Email + GitHub

1. Create a dedicated ProtonMail: https://proton.me/mail (free)
2. Create a new GitHub account with that email
3. Fork `paleyzpl/EstyAssistant` into the new GitHub account (or transfer the repo)

### Step 2: Supabase (DB + storage) — 5 min

1. Go to https://supabase.com → Sign up with your ProtonMail
2. Create a new project (any name). Save the database password.
3. Once the project is ready, grab these values:
   - **Project URL**: Settings → General → Project URL (e.g. `https://abc.supabase.co`)
   - **DB connection string**: Settings → Database → Connection string → **Session mode** (looks like `postgresql://postgres.xxx:[email protected]:5432/postgres`)
   - **S3 credentials**: Settings → Storage → S3 Connection → Generate new keys. Copy **Access Key ID** and **Secret Access Key**.
4. Create a storage bucket:
   - Storage → New bucket → name: `etsy-assistant-images` → Public: **off**

### Step 3: Fly.io (backend) — 5 min

1. Sign up: https://fly.io/app/sign-up
2. Add a payment method (free tier won't charge, but they require one on file). Use Privacy.com or Revolut virtual card with a $5/month limit.
3. Install the CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
4. Log in:
   ```bash
   flyctl auth login
   ```

### Step 4: Anthropic API — 2 min

1. Go to https://console.anthropic.com
2. Sign up → Create API key
3. Save the key (starts with `sk-ant-...`)

### Step 5: Etsy API (optional, for publishing) — 2 min

1. Go to https://www.etsy.com/developers
2. Create an app → get the API key (keystring)

### Step 6: Deploy Backend — 1 command

```bash
git clone https://github.com/YOUR_USERNAME/EstyAssistant.git
cd EstyAssistant
./scripts/setup-free.sh
```

The script will prompt for:
- Supabase project URL
- Supabase database URL
- Supabase S3 credentials
- Anthropic API key
- Etsy API key (optional)

It then:
1. Creates a Fly.io app
2. Sets all secrets
3. Deploys the backend container
4. Prints the API URL (e.g. `https://etsy-assistant-xyz.fly.dev`)

### Step 7: Deploy Frontend to Vercel — 3 min

1. Go to https://vercel.com → Sign in with your new GitHub account
2. Add New Project → import `YOUR_USERNAME/EstyAssistant`
3. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Next.js (auto-detected)
   - **Environment Variables**: `NEXT_PUBLIC_API_URL` = `https://etsy-assistant-xyz.fly.dev` (from Step 6)
4. Deploy

### Step 8: Update Backend CORS

Once you have your Vercel URL (e.g. `https://etsy-assistant-xyz.vercel.app`):

```bash
flyctl secrets set -a YOUR_FLY_APP_NAME \
    CORS_ORIGINS="https://etsy-assistant-xyz.vercel.app,http://localhost:3000"
```

### Step 9: Test End-to-End

1. Visit your Vercel URL
2. Drop a sketch, pick sizes, click Process
3. You should see before/after preview

### Auto-Deploy on Push (optional)

1. Get a Fly API token: `flyctl tokens create deploy`
2. In your GitHub repo → Settings → Secrets → Actions → New secret
   - Name: `FLY_API_TOKEN`
   - Value: (the token from flyctl)
3. Edit `.github/workflows/deploy.yml` and change `if: ${{ false }}` to `if: ${{ true }}`
4. Every push to main now auto-deploys backend to Fly, frontend to Vercel

### Costs Summary (Path A)

| Service | Free Tier | Cost |
|---------|-----------|------|
| Vercel Hobby | Unlimited personal projects | $0 |
| Fly.io | 3 shared VMs, 3GB storage | $0 |
| Supabase | 500MB DB, 1GB storage, 2GB egress | $0 |
| Anthropic API | Pay-per-use | ~$0.05-0.10/image |
| **Total** | | **$0-5/month** (dominated by Anthropic usage) |

---

## Path B: AWS

**Stack**: Vercel (frontend) + AWS Lambda (backend) + S3 + DynamoDB
**Cost**: ~$1-5/month after first year (AWS free tier)
**Time**: ~45 minutes (includes AWS account setup)

### Prerequisites (local machine)

1. **AWS CLI v2**: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html
2. **AWS SAM CLI**: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
3. **Docker Desktop**: https://www.docker.com/products/docker-desktop/
4. **Node.js 22+**: https://nodejs.org/
5. **Git**: to clone the repo

### Step 1: AWS Account Setup

1. Sign up at https://aws.amazon.com/
2. Create an IAM user `etsy-assistant-deploy` with policies:
   - `AmazonS3FullAccess`
   - `AmazonDynamoDBFullAccess`
   - `AWSLambda_FullAccess`
   - `AmazonAPIGatewayAdministrator`
   - `AmazonEC2ContainerRegistryFullAccess`
   - `AWSCloudFormationFullAccess`
   - `IAMFullAccess`
3. Generate access keys for the IAM user
4. Run `aws configure` to set them

### Step 2: Anthropic API Key

1. https://console.anthropic.com → Create Key
2. Save as `sk-ant-...`

### Step 3: Deploy Backend

```bash
git clone https://github.com/paleyzpl/EstyAssistant.git
cd EstyAssistant
export ANTHROPIC_API_KEY="sk-ant-..."
./scripts/deploy-backend.sh
```

Prints the API URL at the end.

### Step 4: Deploy Frontend to Vercel

Same as Path A Step 7.

### Step 5: Update CORS and Redeploy

```bash
export CORS_ORIGINS="https://etsy-assistant-xyz.vercel.app,http://localhost:3000"
./scripts/deploy-backend.sh
```

### Costs (Path B)

| Service | Free Tier | After Free Tier |
|---------|-----------|----------------|
| Lambda | 1M requests + 400K GB-s | ~$0 at low volume |
| API Gateway | 1M calls (12 months) | ~$0 |
| S3 | 5 GB (12 months) | ~$0.50/month |
| DynamoDB | 25 GB + 25 RCU/WCU | ~$0 |
| ECR | 500 MB | ~$0 |
| **Total** | | **$1-5/month** |

---

## Path C: AWS from GitHub Actions (no terminal)

**Stack**: Vercel (frontend) + AWS Lambda + S3 + DynamoDB (same as Path B)
**Cost**: same as Path B (~$1-5/month after free tier)
**Time**: ~30 minutes (all done in a web browser)

Use this path when you want the AWS stack but have no local dev environment — the GitHub Actions runner builds the Docker image and runs `sam deploy` for you. Credentials are federated via OIDC, so no long-lived AWS access keys are stored anywhere.

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
   - GitHub organization: `paleyzpl`
   - GitHub repository: `EstyAssistant`
   - (Leave branch empty to allow any branch; tighten later)
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

Same as Path A Step 7, with `NEXT_PUBLIC_API_URL` set to the `ApiUrl` from Step 5.

### Step 7: Fix CORS and redeploy

1. Back in GitHub → Settings → Variables → edit `CORS_ORIGINS` to include your Vercel URL:
   `https://your-app.vercel.app,http://localhost:3000`
2. Actions → Deploy Backend → Run workflow again. `sam deploy` picks up the new parameter and updates the Lambda env var.

### Tearing down

Running `aws cloudformation delete-stack --stack-name etsy-assistant` from any machine with AWS creds works. Or from the AWS Console → CloudFormation → select the stack → **Delete**. Then delete the ECR repo and the S3 bucket (they're retained by default).

### Troubleshooting

- **`Not authorized to perform sts:AssumeRoleWithWebIdentity`** — the trust policy's `sub` condition doesn't match. Check it reads `repo:paleyzpl/EstyAssistant:*`.
- **`AccessDenied` during `sam deploy`** — role is missing a permission. Either attach `PowerUserAccess` + `IAMFullAccess`, or read the error to add the specific action to your inline policy.
- **First build is slow (~5 min)** — Docker layers are uncached on the runner. Subsequent deploys reuse ECR image layers.

---

## Local Development

Both paths support local development via `uvicorn`:

```bash
# Backend (port 8000) — pick your backend env vars
cd backend
uv sync --group dev

# For Path A (Supabase local):
export STORAGE_BACKEND=supabase DB_BACKEND=supabase
export SUPABASE_URL="..." SUPABASE_DB_URL="..." SUPABASE_S3_ACCESS_KEY_ID="..." SUPABASE_S3_SECRET_ACCESS_KEY="..."
export S3_BUCKET="etsy-assistant-images" ANTHROPIC_API_KEY="sk-ant-..."

# For Path B (AWS local):
export S3_BUCKET="your-bucket" AWS_REGION="us-east-1" ANTHROPIC_API_KEY="sk-ant-..."

PYTHONPATH=../src:src uvicorn api.main:app --reload
```

```bash
# Frontend (port 3000)
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## Switching Between Paths

The backend code is backend-agnostic. Switch via env vars:

| Component | AWS | Supabase |
|-----------|-----|----------|
| Storage | `STORAGE_BACKEND=s3` | `STORAGE_BACKEND=supabase` |
| Database | `DB_BACKEND=dynamo` | `DB_BACKEND=supabase` |

You can even mix (e.g. AWS storage with Supabase DB). No code changes needed.

---

## Troubleshooting

### Fly.io deploy fails with "out of memory"
- Image processing needs ~512MB. Increase memory in `fly.toml`:
  ```toml
  [[vm]]
    memory = "1gb"
  ```

### Supabase Storage upload 403
- Check bucket policies: Supabase Dashboard → Storage → Bucket → Policies
- For simplicity in a single-user app, make the bucket accept writes via your S3 credentials

### CORS errors
- Update `CORS_ORIGINS` via `flyctl secrets set` and redeploy

### Frontend build fails on Vercel
- Make sure **Root Directory** is set to `frontend` in Vercel project settings

---

## Tear Down

**Path A (free):**
```bash
flyctl apps destroy YOUR_FLY_APP_NAME
# Delete Supabase project from their dashboard
# Delete Vercel project from their dashboard
```

**Path B (AWS):**
```bash
aws cloudformation delete-stack --stack-name etsy-assistant --region us-east-1
aws s3 rb s3://etsy-assistant-images-ACCOUNT_ID --force
aws ecr delete-repository --repository-name etsy-assistant --force --region us-east-1
```
