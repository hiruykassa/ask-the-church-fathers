# Moving ask-the-early-church to AWS — how the migration went

This is the record of a migration that is now complete. The app runs entirely on
AWS; Render, Netlify, and Cloudflare R2 are no longer in the serving path. Kept
here for the reasoning behind each choice and, more usefully, the problems hit
along the way — see [gotchas](#gotchas-we-hit-deploying-the-backend-phase-3).

## What moved (and to what)

The app previously ran across three services:

| Piece | Before | Now on AWS | What the AWS thing is, in plain terms |
|-------|--------|------------|----------------------------------------|
| React frontend | Netlify | **S3 + CloudFront** | S3 is a folder in the cloud that holds files. CloudFront is a global cache that serves those files fast and over HTTPS. |
| Flask backend | Render | **App Runner** | You hand AWS your Docker container; it runs it, gives it a web address, HTTPS, and auto-restarts it. No servers to manage. |
| `database.db` (663 MB) | Cloudflare R2 | **S3** | Same idea as R2 — object storage. The backend downloads the file on startup via `prestart.sh`. |

The API keys (Voyage, Gemini, Groq) were unaffected — they're third-party services
the new backend simply points at.

## Why App Runner and not the scarier options

The alternatives were EC2, ECS, Fargate, and Lambda. For a single Flask container
that keeps a big embedding matrix in memory, App Runner was the gentlest: it reads
the existing `Dockerfile`, builds it, runs it, and hands back an
`https://…awsapprunner.com` URL. No virtual machines, no load balancers, no
networking wired up by hand. Graduating to ECS later remains possible; nothing
here blocks it.

## The order it went in

The new stack was built *beside* the old one, with DNS switched only at the end,
so a problem at any earlier phase left the live site untouched.

1. **Account + guardrails** — set up the AWS account, turned on a spending alarm to
   avoid surprise bills, and created a non-root login. Installed the AWS CLI so the
   later steps could run from the Terminal.
2. **Database → S3** — created a private S3 bucket, uploaded `database.db`, and got
   a URL the backend could fetch on boot.
3. **Backend → App Runner** — pushed the Docker image, set the environment variables
   and secrets, deployed, and confirmed `/api/health` returned OK. This is the phase
   that produced all three gotchas below.
4. **Frontend → S3 + CloudFront** — built the React app pointed at the new backend
   URL, uploaded it, and put CloudFront in front.
5. **Test in parallel** — exercised the whole AWS stack while Render/Netlify stayed
   live. Search, browse, the works.
6. **Cut over** — pointed the domain at CloudFront + App Runner, watched it, and
   once it was proven, shut off the Render and Netlify traffic.

## Monthly cost

For this low-traffic app: App Runner ~$25–50, S3 + CloudFront a few dollars, data
transfer negligible. A budget alarm was set in phase 1.

## Ground rules the migration followed (from CLAUDE.md)

- API keys were never printed, pasted into chat, or committed. On AWS they live in
  SSM Parameter Store and are referenced by ARN, so App Runner injects them at
  runtime and no key value appears in any config file.
- Every command touching a real credential was run by the owner in their own
  Terminal.

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

*All six phases are complete. For the resulting production architecture, and the
gaps the migration left open, see the Architecture and Roadmap sections of the
[README](../README.md).*
