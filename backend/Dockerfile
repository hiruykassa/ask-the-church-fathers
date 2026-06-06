# Backend image for AWS migration (ECS/Fargate/EC2).
# Render uses native Python today; this Dockerfile is for the AWS move and
# for local prod-parity testing:
#
#   docker build -t aetc-backend backend/
#   docker run -p 5001:5001 \
#       -e ANTHROPIC_API_KEY=... -e VOYAGE_API_KEY=... \
#       -e PRODUCTION=1 -e ALLOWED_ORIGIN=http://localhost:5173 \
#       -e DB_URL=https://... aetc-backend

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# curl needed by prestart.sh; everything else is in wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
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

# Render and ECS both inject $PORT; fall back to 5001 for local docker run.
# -w 2 keeps memory bounded (each worker holds the full embedding matrix).
CMD ["sh", "-c", "./prestart.sh && exec gunicorn -w 2 -b 0.0.0.0:${PORT:-5001} --timeout 60 app:app"]
