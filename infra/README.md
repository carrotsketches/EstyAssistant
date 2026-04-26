# AWS Deployment Guide

This is the step-by-step bootstrap for deploying the backend to AWS. The target stack is Lambda (container) + API Gateway + S3 + DynamoDB, defined in `infra/template.yaml`. Once bootstrapped, deploys run from GitHub Actions (`.github/workflows/deploy.yml`) via OIDC — no long-lived AWS keys live in the repo.

> Fly.io and Supabase are **not** used. Do not add code or docs that reference them.

## 0. Prerequisites

- AWS account (root email + billing enabled).
- Local tools (only needed if you want to deploy from your laptop instead of CI):
  - AWS CLI v2 — <https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html>
  - SAM CLI — <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html>
  - Docker
- Anthropic API key — <https://console.anthropic.com>
- (Phase C) Etsy developer app — <https://developers.etsy.com>

## 1. Bootstrap AWS (one-time)

### 1a. Create an admin IAM user for bootstrap

In the AWS console: IAM → Users → **Create user** → attach `AdministratorAccess`. Generate an access key, then locally:

```bash
aws configure   # paste key, secret, region us-east-1, output json
aws sts get-caller-identity   # sanity check
```

This admin user is only used to lay down the OIDC trust below. After that, CI uses its own role.

### 1b. Create the GitHub OIDC provider + deploy role

Save this as `infra/bootstrap-oidc.yaml` only if you want it tracked; otherwise paste the body inline. Replace `<GH_OWNER>/<GH_REPO>` with `carrotsketches/EstyAssistant`.

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Description: GitHub Actions OIDC provider + deploy role for Etsy Assistant
Parameters:
  GitHubOrg:    { Type: String, Default: carrotsketches }
  GitHubRepo:   { Type: String, Default: EstyAssistant }
Resources:
  GitHubOIDCProvider:
    Type: AWS::IAM::OIDCProvider
    Properties:
      Url: https://token.actions.githubusercontent.com
      ClientIdList: [sts.amazonaws.com]
      ThumbprintList: [6938fd4d98bab03faadb97b34396831e3780aea1]
  DeployRole:
    Type: AWS::IAM::Role
    Properties:
      RoleName: etsy-assistant-deploy
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal: { Federated: !GetAtt GitHubOIDCProvider.Arn }
            Action: sts:AssumeRoleWithWebIdentity
            Condition:
              StringEquals:
                token.actions.githubusercontent.com:aud: sts.amazonaws.com
              StringLike:
                token.actions.githubusercontent.com:sub: !Sub "repo:${GitHubOrg}/${GitHubRepo}:*"
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/AdministratorAccess  # tighten after first deploy
Outputs:
  RoleArn: { Value: !GetAtt DeployRole.Arn }
```

Deploy it:

```bash
aws cloudformation deploy \
  --stack-name etsy-assistant-oidc \
  --template-file infra/bootstrap-oidc.yaml \
  --capabilities CAPABILITY_NAMED_IAM
aws cloudformation describe-stacks --stack-name etsy-assistant-oidc \
  --query 'Stacks[0].Outputs' --output table
```

Copy the `RoleArn` — you'll paste it into GitHub next.

> The bootstrap role uses `AdministratorAccess` to keep the first deploy unblocked. After Phase A succeeds, replace it with a least-privilege policy (CloudFormation, IAM PassRole, S3, DynamoDB, Lambda, ECR, API Gateway, CloudWatch, SNS, SSM only on the stack's resources).

## 2. Configure GitHub repo (one-time)

Repo settings → **Secrets and variables → Actions**:

**Variables**
- `AWS_ROLE_ARN` — the `RoleArn` from step 1b
- `CORS_ORIGINS` — comma-separated, e.g. `https://esty-assistant.vercel.app,http://localhost:3000`
- `FRONTEND_URL` — e.g. `https://esty-assistant.vercel.app`
- `ALARM_EMAIL` — email for CloudWatch alarms (optional; leave unset to skip SNS)

**Secrets**
- `ANTHROPIC_API_KEY` — from <https://console.anthropic.com>
- `ETSY_API_KEY` — leave empty until Phase C

## 3. First deploy (Phase A)

Trigger the workflow:

- GitHub UI: **Actions → Deploy Backend → Run workflow** (defaults are fine: stack `etsy-assistant`, region `us-east-1`).
- Or, if you have `gh` locally: `gh workflow run deploy.yml`.

The workflow does: checkout → assume `AWS_ROLE_ARN` via OIDC → `sam build` → `sam deploy` (resolves ECR repo + S3 staging bucket automatically) → prints stack outputs.

When it finishes, capture from the "Show stack outputs" step:
- `ApiUrl` — e.g. `https://abc123.execute-api.us-east-1.amazonaws.com`
- `BucketName` — e.g. `etsy-assistant-images-123456789012`

### Local-only alternative

If you'd rather deploy from your laptop (skip GitHub setup):

```bash
export ANTHROPIC_API_KEY=sk-...
export CORS_ORIGINS=http://localhost:3000
./scripts/deploy-backend.sh
```

## 4. Wire the frontend (Phase B)

In Vercel project settings for the `frontend/` directory:

1. Set env var `NEXT_PUBLIC_API_URL` = `ApiUrl` from step 3.
2. Redeploy. Verify in browser devtools: `fetch('${ApiUrl}/health')` returns 200.
3. If your Vercel domain isn't already in `CORS_ORIGINS`, update the `CORS_ORIGINS` GitHub variable and re-run the deploy workflow.

## 5. Etsy OAuth (Phase C)

1. Register the app at <https://developers.etsy.com>. Set the callback URL to `https://<vercel-domain>/auth/etsy/callback`.
2. In GitHub → secrets, set `ETSY_API_KEY` to the Etsy client ID. (If/when we add an OAuth client secret, store it the same way and surface it through `template.yaml` parameters.)
3. Re-run the **Deploy Backend** workflow so Lambda picks up the new env var.
4. End-to-end smoke test: from the frontend, click **Connect Etsy** → process a sketch → publish a draft listing → confirm it appears as a draft on Etsy.

## 6. Hardening (Phase D)

- **CloudWatch alarms** — already in `template.yaml` (Lambda errors/throttles/duration, API 5xx). Set `ALARM_EMAIL` to receive SNS notifications and confirm the subscription email AWS sends.
- **S3 lifecycle** — already in template (`uploads/` 7d, `processed/` 30d). Adjust if needed.
- **DynamoDB** — `PAY_PER_REQUEST` (already set). No knobs to turn until usage justifies it.
- **Tighten the deploy role** — replace `AdministratorAccess` on `etsy-assistant-deploy` with a scoped policy. Easiest path: capture the actions IAM Access Analyzer reports after a few deploys, then write the inline policy.
- **Custom domain (optional)** — Route 53 hosted zone + ACM cert in `us-east-1` + API Gateway custom domain mapping. Add to `template.yaml` once you have a domain.

## Stack outputs cheat sheet

```bash
aws cloudformation describe-stacks \
  --stack-name etsy-assistant \
  --query 'Stacks[0].Outputs' --output table
```

| Output | Used for |
|--------|----------|
| `ApiUrl` | `NEXT_PUBLIC_API_URL` in Vercel |
| `BucketName` | Verify uploads/ and processed/ prefixes in S3 console |

## Teardown

```bash
aws cloudformation delete-stack --stack-name etsy-assistant
# Then empty + delete the OIDC stack only if you're done with the repo:
aws cloudformation delete-stack --stack-name etsy-assistant-oidc
```

S3 buckets with objects won't delete via CloudFormation alone — empty `etsy-assistant-images-<account>` first.
