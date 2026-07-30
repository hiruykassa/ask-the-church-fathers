# Backend image for AWS App Runner (the production runtime).
#
# App Runner pulls this from ECR and must be built for linux/amd64 — the
# service does not run arm64 images, so builds from an Apple Silicon machine
# need an explicit --platform.
#
# On start the container runs prestart.sh, which downloads database.db from
# S3 using the App Runner instance role, then execs gunicorn.
#
# Local prod-parity run (needs AWS credentials in the environment for the S3
# fetch, or an existing backend/database.db, which prestart.sh will keep):
#
#   docker build --platform linux/amd64 -t aetc-backend backend/
#   docker run -p 5001:5001 \
#       -e VOYAGE_API_KEY=... -e GEMINI_API_KEY=... -e GROQ_API_KEY=... \
#       -e PRODUCTION=1 -e ALLOWED_ORIGIN=http://localhost:5173 \
#       -e DB_URL=s3://your-bucket/database.db aetc-backend

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# prestart.sh downloads the DB with boto3, not curl. Only the TLS trust store
# is needed here; everything else ships as wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first so code changes don't bust the layer cache.
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code.
COPY . .

# Drop privileges.
RUN useradd --create-home --uid 1000 aetc \
    && chown -R aetc:aetc /app \
    && chmod +x prestart.sh
USER aetc

EXPOSE 5001

# App Runner injects $PORT; fall back to 5001 for local docker run.
# -w 1 keeps memory bounded (each worker holds the full embedding matrix) and
# makes the in-memory rate limiter exact. Scale workers only on a larger box.
# --threads 8 lets one worker overlap requests: a search spends most of its
# wall time blocked on Gemini/Voyage HTTP and on SQLite, all of which release
# the GIL, so without threads a single slow search serializes every other
# visitor. Threads share the process's embedding matrix, so this costs no
# extra memory.
CMD ["sh", "-c", "./prestart.sh && exec gunicorn -w 1 --threads 8 -b 0.0.0.0:${PORT:-5001} --timeout 60 app:app"]
