# Deploying, testing, and CI

Deploys run from GitHub Actions on push to `main` — see
[`github-actions-deploy.md`](github-actions-deploy.md) for the workflow and its
one-time OIDC setup. The manual sequence below is what that workflow automates,
and what you fall back to when it breaks.

## Deploying


Deploys run from GitHub Actions on push to `main`, after both test jobs pass — see [`docs/github-actions-deploy.md`](github-actions-deploy.md) for the workflow and its one-time OIDC setup. **The workflow is inert until that setup is done**; until then, and any time you need to ship by hand, the manual sequence below is authoritative. It is also what the workflow automates, so it stays worth understanding.

### Backend → App Runner

The ECR repository is **`ask-the-early-church-api`**, matching the `ImageIdentifier` the live service pulls. Pushing to `ask-the-early-church` (no suffix) creates a repo nothing reads from, and the subsequent `start-deployment` silently redeploys the *old* image.

```bash
# 1. Build for x86_64 with attestations off (both are required — see gotchas)
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -t <account-id>.dkr.ecr.us-east-2.amazonaws.com/ask-the-early-church-api:latest backend/

# 2. Push to ECR
aws ecr get-login-password --region us-east-2 \
  | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-2.amazonaws.com
docker push <account-id>.dkr.ecr.us-east-2.amazonaws.com/ask-the-early-church-api:latest

# 3. Roll the service, then confirm it came back healthy
aws apprunner start-deployment --service-arn <service-arn> --region us-east-2
curl -s https://<service>.us-east-2.awsapprunner.com/api/health | jq
```

`/api/health` should report `status: ok`, `embeddings_loaded: 52870`, and all three providers `true`. **Boot takes ~135 seconds** (measured 2m53s on 2026-07-31, 3m05s on 2026-08-04): the 633 MB database downloads from S3, then 52,870 embeddings load into RAM before gunicorn answers anything.

> **`update-service` does not ship code.** An earlier version of this section claimed that because the tag is `:latest`, any `update-service` call also re-pulls the image, so an env-var change and a code change could share one deployment. **That is wrong**, and it bit a real deploy on 2026-07-31: the new image was pushed to ECR, `update-service` was called to add `SENTRY_DSN`, the service reported a successful deployment — and the *old* code kept serving. `update-service` applies configuration; it does not re-pull an unchanged tag. It was caught only because the new `Cache-Control` headers and the raised `/api/health` limit were missing from the live responses.
>
> Ship code with **`start-deployment`**, or pin `ImageIdentifier` to an explicit digest so the identifier itself changes. If a release carries both a config change and a code change, expect **two** restarts at ~135s each, and verify the code actually landed by checking for something only the new build emits.

> **Both `update-service` and `update-distribution` replace configuration wholesale.** They do not merge. Every call must round-trip the complete object — fetch the current config, change only the field you intend to change, send the whole thing back. A partial payload silently drops everything omitted. On 2026-07-31 a payload was about to ship without `PRODUCTION=1`, which would have disabled `ProxyFix` (`app.py:745`) and collapsed every visitor into a single rate-limit bucket — one user running ten searches would have locked out the whole site.

### Frontend → S3 + CloudFront

```bash
# VITE_API_URL is baked into the bundle at build time — a wrong value ships broken.
# Omitting it no longer can: vite.config.js fails the build when it is unset or
# is not an absolute http(s) URL, before any artifact exists to upload.
# build:deploy runs generate:seo → vite build → generate:meta, in that order.
VITE_API_URL=https://<service>.us-east-2.awsapprunner.com npm run build:deploy

aws s3 sync dist/ s3://ask-the-early-church-frontend-<account-id>/ --delete
aws cloudfront create-invalidation --distribution-id <dist-id> --paths '/*'
```

`generate:meta` needs `backend/database.db` present locally (633 MB, gitignored). If it is missing the script exits non-zero rather than shipping a build with homepage meta on every route.

The sync now moves ~3,100 extra small files, so expect minutes rather than seconds on the first run; subsequent syncs only transfer what changed.

**Verify after every frontend deploy** — a `--delete` sync destroyed `og-image.png` once:

```bash
curl -sI https://asktheearlychurch.com/og-image.png | grep -i content-type   # must be image/png
curl -s  https://asktheearlychurch.com/read/852 | grep -E 'canonical|<title>' # must be the work, not the homepage
```

The second check is the one that tells you the CloudFront function is still attached. If it returns the homepage title, the static files deployed but nothing is routing to them.

### Changing AWS resource config

Always fetch the current config first, change only the field you intend to change, and send the whole object back — see the wholesale-replace warning under [Backend → App Runner](#backend--app-runner) for what this has already nearly cost.

Two settings worth knowing because they are not editable in place:

- **Autoscaling concurrency is immutable.** Changing it means creating a *new* autoscaling configuration and associating it, not editing the existing one. The live config is `aetc-api` — concurrency 8, min 1, max 25. Concurrency is deliberately matched to gunicorn's `--threads 8` so App Runner scales out when the worker is actually saturated, rather than queueing 92 requests inside one instance first.
- **Health check timings** are interval 10s, timeout 5s, healthy 1, unhealthy 5. The timeout was raised from 2s because a busy instance answering `/api/health` slowly was indistinguishable from a dead one, and replacement costs a ~135s rebuild — which under sustained load loops.

---

## Testing & CI


[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every push to `main` and every pull request:

| Job | What it does |
|-----|--------------|
| **Backend smoke tests** | Python 3.13, installs `backend/requirements.txt`, fetches the database via `prestart.sh` when the `DB_URL` secret is set, then runs `pytest -q`. Skips the tests with a clear log line when no database is available rather than failing opaquely |
| **Frontend lint, test, build** | Node 20, `npm ci`, `npm run lint`, `npm test` (Vitest over `src/utils`, no keys or DB needed), then `npm run build` against a placeholder `VITE_API_URL` — it verifies the bundle compiles, not that it points anywhere real |

Tests live in `backend/tests/`: `test_parsing.py` covers query parsing and scripture-reference detection (no database needed); `test_smoke.py` exercises the live endpoints against a real corpus.

Coverage is deliberately thin — smoke tests over the paths most likely to break silently, not a coverage target. The frontend has no test suite; see [Known gaps](#known-gaps).

---
