# Moving ask-the-early-church to AWS — a beginner's runbook

This is our shared map. We go one phase at a time, together. Nothing here touches
your live site until the very last step, so you can stop and breathe at any point.

## What we're moving (and to what)

Right now your app lives on three services:

| Piece | Today | Moving to on AWS | What the AWS thing is, in plain terms |
|-------|-------|------------------|----------------------------------------|
| React frontend | Netlify | **S3 + CloudFront** | S3 is a folder in the cloud that holds files. CloudFront is a global cache that serves those files fast and over HTTPS. |
| Flask backend | Render | **App Runner** | You hand AWS your Docker container; it runs it, gives it a web address, HTTPS, and auto-restarts it. No servers to manage. |
| `database.db` (663 MB) | Cloudflare R2 | **S3** | Same idea as R2 — object storage. Your backend downloads the file on startup (it already does this via `prestart.sh`). |

Your API keys (Voyage, Gemini, Groq) stay exactly as they are — they're third-party
services we just point the new backend at.

## Why App Runner and not the scarier options

You'll hear about EC2, ECS, Fargate, Lambda. For a single Flask container that keeps
a big embedding matrix in memory, App Runner is the gentlest: it reads your existing
`Dockerfile`, builds it, runs it, and hands you an `https://…awsapprunner.com` URL.
No virtual machines, no load balancers, no networking to wire up by hand. We can
always graduate to ECS later; nothing we do now blocks that.

## The order we'll go in

We build the new stack *beside* the old one and only switch DNS at the end. If
anything looks wrong, the live site never noticed.

1. **Account + guardrails** — make sure you have an AWS account, turn on a spending
   alarm so there are no surprise bills, and create a login that isn't the root
   account. Install the AWS CLI so we can do steps from your Terminal.
2. **Database → S3** — create a private S3 bucket, upload `database.db`, and get a
   URL the backend can fetch on boot.
3. **Backend → App Runner** — push the Docker image, set the environment variables
   and secrets, deploy, and confirm `/api/health` returns OK.
4. **Frontend → S3 + CloudFront** — build the React app pointed at the new backend
   URL, upload it, and put CloudFront in front.
5. **Test in parallel** — exercise the whole AWS stack while Render/Netlify stay
   live. Search, browse, the works.
6. **Cut over** — point your domain at CloudFront + App Runner. Watch it. Once it's
   proven, turn off Render and Netlify.

## Rough monthly cost

For a low-traffic app: App Runner ~$25–50, S3 + CloudFront a few dollars, data
transfer negligible. We'll set a budget alarm in step 1 so you're never surprised.

## Ground rules we're keeping (from your CLAUDE.md)

- API keys never get printed, pasted into chat, or committed. On AWS they go into
  App Runner's secret fields (or AWS Secrets Manager) — you type them, not me.
- You run any command that touches a real credential in your own Terminal.

## Gotchas we hit deploying the backend (phase 3)

All three cause a `CREATE_FAILED` with an unhelpful "health check failed / check
your port number" message, so they're worth knowing in advance:

- **App Runner is x86_64-only** — no ARM/Graviton, in console or CLI. Build with
  `docker build --platform linux/amd64 …` no matter what your dev machine is (e.g.
  Apple Silicon). An arm64 image pulls fine but the container dies instantly with
  `exec format error` in the application logs.
- **Disable buildx attestations** — modern Docker Desktop/buildx pushes an OCI
  *image index* with a provenance/attestation manifest, which App Runner can't
  launch (it pulls the image, then fails with *zero* application logs). Build with
  `--provenance=false --sbom=false` so ECR gets a single-platform image manifest.
- **SecureString secrets need `kms:Decrypt`** — an instance role with only
  `ssm:GetParameters` can't read SecureString SSM params; App Runner fails to inject
  `RuntimeEnvironmentSecrets` before the container starts (again, no logs). Add
  `kms:Decrypt` scoped with `Condition: kms:ViaService = ssm.<region>.amazonaws.com`
  (works for the AWS-managed `alias/aws/ssm` key, which has no fixed ARN to target).

---

*Progress is tracked in the task list. We'll check items off as we finish each phase.*
