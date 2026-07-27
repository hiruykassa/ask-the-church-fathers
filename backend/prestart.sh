#!/usr/bin/env bash
# Hydrate database.db from object storage at container/process start.
#
# AWS: invoke from the Docker CMD (App Runner runs this automatically).
#
# Required env var:
#   DB_URL — s3://bucket/key → downloaded via boto3, using whatever AWS
#            credentials are ambient (App Runner's instance role — no keys
#            in the URL or env).
#
# Idempotent: skips download if database.db already exists on the local disk
# (useful for local dev).

set -euo pipefail

DB_FILE="${DB_FILE:-database.db}"

if [ -f "$DB_FILE" ]; then
  echo "[prestart] $DB_FILE already present — skipping download"
  exit 0
fi

if [ -z "${DB_URL:-}" ]; then
  echo "[prestart] ERROR: DB_URL is not set and $DB_FILE does not exist" >&2
  exit 1
fi

if [[ "$DB_URL" != s3://* ]]; then
  echo "[prestart] ERROR: DB_URL must be an s3://bucket/key URL (got ${DB_URL})" >&2
  exit 1
fi

echo "[prestart] Fetching $DB_FILE from S3 ($DB_URL) via instance role"
DB_URL="$DB_URL" DB_FILE="$DB_FILE" python3 - <<'PYEOF'
import os, sys
import boto3

url = os.environ["DB_URL"]
bucket, _, key = url[len("s3://"):].partition("/")
if not bucket or not key:
    print(f"[prestart] ERROR: malformed DB_URL {url!r} (expected s3://bucket/key)", file=sys.stderr)
    sys.exit(1)

dest = os.environ["DB_FILE"]
try:
    boto3.client("s3").download_file(bucket, key, dest)
except Exception as e:
    print(f"[prestart] ERROR: S3 download failed: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

# Cheap sanity check — SQLite files start with this magic string.
if ! head -c 16 "$DB_FILE" | grep -q "SQLite format 3"; then
  echo "[prestart] ERROR: downloaded file is not a SQLite database" >&2
  rm -f "$DB_FILE"
  exit 1
fi

echo "[prestart] $DB_FILE ready ($(wc -c < "$DB_FILE") bytes)"
