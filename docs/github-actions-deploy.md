# Automated deploys — GitHub Actions + OIDC

Before this existed, pushing to GitHub ran tests and nothing else. Deploys were
a human running build, push, `start-deployment`, sync, and invalidate by hand —
which is how the site once served old code while the console reported a
successful deployment, and how `og-image.png` was deleted by a `--delete` sync.

`.github/workflows/ci.yml` now deploys on push to `main` after both test jobs
pass. **No long-lived AWS keys are stored in GitHub.** The workflow assumes an
IAM role through GitHub's OIDC provider, scoped to this repository.

## What the workflow does

| Job | Runs when |
|-----|-----------|
| `backend` | every push and PR — pytest |
| `frontend` | every push and PR — lint + build |
| `changes` | push to `main` — decides which halves need deploying |
| `deploy-backend` | `backend/**` changed, or forced via `workflow_dispatch` |
| `deploy-frontend` | `src/`, `public/`, `tools/`, `index.html`, `package*.json`, `vite.config.js`, or `eslint.config.js` changed, or forced |

Path scoping matters: a docs-only commit should not trigger a ~135-second
backend restart or a 3,100-file S3 sync. To deploy anyway, use **Actions → CI →
Run workflow**, which forces both halves unless you narrow it with the inputs.

Two behaviours are deliberate and should not be "simplified" later:

- **`start-deployment`, never `update-service`.** `update-service` applies
  configuration and does *not* re-pull an unchanged `:latest` tag. On
  2026-07-31 it reported a successful deployment while the old code kept
  serving. The workflow also tags each image with the commit SHA, so there is
  always an immutable identifier to roll back to.
- **Health is verified by polling `/api/health` until `embeddings_loaded > 0`,
  not by the service reaching `RUNNING`.** Boot is the slow part: 633 MB of
  database from S3, then 52,869 embeddings into RAM.

  Measured on the first backend deploy (2026-07-31): `OPERATION_IN_PROGRESS` →
  `RUNNING` took 2m53s, and `embeddings_loaded: 52869` was already true on the
  first poll about a second later. So in practice `RUNNING` *did* imply ready —
  an earlier draft of this file asserted the opposite as a general fact, which
  was wrong.

  The reason it holds is worth understanding rather than relying on: App Runner
  gates the deployment on its own configured health check, and that check is
  pointed at `/api/health` — an application endpoint that cannot answer until
  gunicorn is up and the embeddings are loaded. **Repoint the health check at a
  static path and that guarantee silently disappears.** The explicit poll costs
  a second and keeps the workflow correct regardless, so it stays.

The frontend job downloads `database.db` before building, because
`npm run build:deploy` runs `generate_seo.py` and `generate_static_meta.py`,
both of which read SQLite directly. It then verifies the build before syncing
(`og-image.png` is a real PNG, >3,000 per-route files exist, sitemap has >10,000
URLs) and verifies the live site afterwards with a cache-busting query string —
without one, an edge can serve a stale object and the check passes for the
wrong reason.

## One-time AWS setup

Run once. Requires IAM permissions.

### 1. GitHub as an OIDC identity provider

Skip if the account already has one — check `aws iam list-open-id-connect-providers`.

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```

### 2. Trust policy

Save as `trust-policy.json`. Replace `<ACCOUNT_ID>` and, if your GitHub user or
repo name differs, `hiruykassa/ask-the-early-church`.

The `sub` condition is what stops any other repository on GitHub from assuming
this role. Keep it pinned to `ref:refs/heads/main` — a wildcard such as
`repo:hiruykassa/ask-the-early-church:*` would let a pull request from a fork
assume a role that can deploy to production.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:hiruykassa/ask-the-early-church:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

```bash
aws iam create-role --role-name aetc-github-deploy \
  --assume-role-policy-document file://trust-policy.json
```

### 3. Permissions policy

Save as `deploy-policy.json`, replacing the placeholders. Scoped to the exact
resources this project uses — no wildcards on buckets or services.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "EcrAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "EcrPush",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ],
      "Resource": "arn:aws:ecr:us-east-2:<ACCOUNT_ID>:repository/ask-the-early-church-api"
    },
    {
      "Sid": "AppRunnerDeploy",
      "Effect": "Allow",
      "Action": [
        "apprunner:StartDeployment",
        "apprunner:DescribeService"
      ],
      "Resource": "<APPRUNNER_SERVICE_ARN>"
    },
    {
      "Sid": "ReadCorpusDatabase",
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::ask-the-early-church-db-<ACCOUNT_ID>/database.db"
    },
    {
      "Sid": "WriteFrontendBucket",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::<FRONTEND_BUCKET>/*"
    },
    {
      "Sid": "ListFrontendBucket",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::<FRONTEND_BUCKET>"
    },
    {
      "Sid": "InvalidateCdn",
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateInvalidation",
        "cloudfront:GetInvalidation"
      ],
      "Resource": "arn:aws:cloudfront::<ACCOUNT_ID>:distribution/<DISTRIBUTION_ID>"
    }
  ]
}
```

```bash
aws iam put-role-policy --role-name aetc-github-deploy \
  --policy-name aetc-deploy --policy-document file://deploy-policy.json
```

Note the role can read `database.db` but cannot write it, and can write the
frontend bucket but not the database bucket. A compromised workflow cannot
destroy the corpus.

## GitHub configuration

**Settings → Secrets and variables → Actions.**

Secrets (all contain the account ID, so they are secrets rather than variables):

| Secret | Value |
|--------|-------|
| `AWS_ROLE_ARN` | `arn:aws:iam::<ACCOUNT_ID>:role/aetc-github-deploy` |
| `ECR_REPOSITORY_URI` | `<ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/ask-the-early-church-api` |
| `APPRUNNER_SERVICE_ARN` | the service ARN |
| `S3_FRONTEND_BUCKET` | frontend bucket name, no `s3://` prefix |
| `CLOUDFRONT_DISTRIBUTION_ID` | distribution ID |
| `DB_URL` | `s3://ask-the-early-church-db-<ACCOUNT_ID>/database.db` |

Variables (optional):

| Variable | Default |
|----------|---------|
| `AWS_REGION` | `us-east-2` |

`VOYAGE_API_KEY`, `GEMINI_API_KEY`, and `GROQ_API_KEY` are only used by the
backend smoke tests. Production reads them from SSM through the App Runner
instance role — they are never passed to a deploy job.

## Verify before trusting it

`DB_URL` was previously set as a secret while the workflow had no AWS
credentials, so `prestart.sh` could never actually download the file and the
backend job skipped its smoke tests while still reporting green. The workflow
now emits a `::warning::` in that case rather than passing silently. **Check
the run log of the next backend job**: if it says smoke tests were skipped, the
role or `DB_URL` is not wired correctly.

First deploy is the one to watch. Push a trivial frontend change and confirm:

1. `changes` outputs `frontend=true`, `backend=false`
2. `deploy-backend` is skipped, `deploy-frontend` runs
3. The verify step reports the per-route canonical for `/read/852`
4. The site still works in a browser

## Rollback

Images are tagged with the commit SHA, so:

```bash
aws apprunner update-service --service-arn <arn> \
  --source-configuration '<full config with ImageIdentifier pinned to the old SHA>'
```

Remember that `update-service` replaces `SourceConfiguration` wholesale — fetch
the current config, change only `ImageIdentifier`, and send the whole object
back. Dropping `PRODUCTION=1` disables `ProxyFix` and collapses every visitor
into a single rate-limit bucket.

For the frontend, both buckets have versioning enabled, so a bad sync can be
recovered object by object from the previous versions.
