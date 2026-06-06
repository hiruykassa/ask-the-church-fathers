#!/usr/bin/env bash
# Hydrate database.db from object storage at container/process start.
#
# Render: invoke from the start command (or as a build step).
# AWS (later): invoke from the Docker CMD or ECS task entrypoint.
#
# Required env var:
#   DB_URL — signed URL or public object URL pointing at database.db
#            (Cloudflare R2 today, S3 on AWS — same interface).
#
# Idempotent: skips download if database.db already exists on the local disk
# (useful for Render persistent disks and local dev).

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

echo "[prestart] Fetching $DB_FILE from object storage"
# -f: fail on HTTP errors, -S: show errors, -L: follow redirects, -o: output path
curl -fSL --retry 3 --retry-delay 2 -o "$DB_FILE" "$DB_URL"

# Cheap sanity check — SQLite files start with this magic string.
if ! head -c 16 "$DB_FILE" | grep -q "SQLite format 3"; then
  echo "[prestart] ERROR: downloaded file is not a SQLite database" >&2
  rm -f "$DB_FILE"
  exit 1
fi

echo "[prestart] $DB_FILE ready ($(wc -c < "$DB_FILE") bytes)"
