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
# Idempotent, but version-aware. An existing database.db is reused ONLY when it
# came from the current S3 object; otherwise it is re-downloaded.
#
# The previous version skipped the download whenever the file existed. That is
# right for local dev and wrong on App Runner: an instance restarted rather than
# replaced keeps whatever corpus it booted with, forever, with one line in the
# log and no version check. It would keep serving a stale corpus after every
# database update — and because the API still answers normally, nothing looks
# broken. The failure is invisible from outside.

set -euo pipefail

DB_FILE="${DB_FILE:-database.db}"
STAMP_FILE="${DB_FILE}.etag"

if [ -f "$DB_FILE" ] && [ -z "${DB_URL:-}" ]; then
  # Local dev: no remote to compare against, so the local file is the truth.
  echo "[prestart] $DB_FILE present and DB_URL unset — using local copy"
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

# Compare the remote object's ETag against the one recorded at last download.
# ETag is used only as a change token, never as a checksum — for a multipart
# upload it is a hash of part hashes, not of the file, so it must not be
# compared against a local md5. All we need is "did the object change".
REMOTE_ETAG="$(DB_URL="$DB_URL" python3 - <<'PYEOF' || true
import os, sys
import boto3
url = os.environ["DB_URL"]
bucket, _, key = url[len("s3://"):].partition("/")
try:
    print(boto3.client("s3").head_object(Bucket=bucket, Key=key)["ETag"].strip('"'))
except Exception as e:
    print(f"[prestart] WARNING: could not read remote ETag: {e}", file=sys.stderr)
PYEOF
)"

if [ -f "$DB_FILE" ] && [ -n "$REMOTE_ETAG" ] && [ -f "$STAMP_FILE" ] \
   && [ "$(cat "$STAMP_FILE")" = "$REMOTE_ETAG" ]; then
  echo "[prestart] $DB_FILE matches the current S3 object — skipping download"
  exit 0
fi

if [ -f "$DB_FILE" ]; then
  # Either the object changed or we cannot tell. Re-downloading is cheap
  # relative to silently serving the wrong corpus.
  echo "[prestart] $DB_FILE is stale or unverifiable — re-downloading"
fi

# Download to a temp path and swap only after it verifies. Replacing the file
# in place would mean a transient S3 failure leaves the instance with *no*
# corpus rather than a stale one — on a deploy the health check would catch
# that, but a plain instance restart would simply fail to boot. A stale corpus
# is recoverable; a missing one is not.
TMP_FILE="${DB_FILE}.part"
trap 'rm -f "$TMP_FILE"' EXIT

echo "[prestart] Fetching $DB_FILE from S3 ($DB_URL) via instance role"
DB_URL="$DB_URL" DB_FILE="$TMP_FILE" python3 - <<'PYEOF'
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

# Cheap sanity check — SQLite files start with this magic string. Runs against
# the temp file, so a corrupt download never replaces a working corpus.
if ! head -c 16 "$TMP_FILE" | grep -q "SQLite format 3"; then
  echo "[prestart] ERROR: downloaded file is not a SQLite database" >&2
  exit 1
fi

# Atomic within the same directory: either the old file or the new one is
# present at $DB_FILE, never a partial write.
mv -f "$TMP_FILE" "$DB_FILE"
trap - EXIT

# Stale WAL/SHM sidecars describe the *previous* file and would be read as if
# they belonged to the new one.
rm -f "${DB_FILE}-wal" "${DB_FILE}-shm"

if [ -n "$REMOTE_ETAG" ]; then
  printf '%s' "$REMOTE_ETAG" > "$STAMP_FILE"
else
  # Could not read the ETag, so the stamp would be a lie. Remove it rather
  # than leave a stale one that could authorise a wrong skip next boot.
  rm -f "$STAMP_FILE"
fi

echo "[prestart] $DB_FILE ready ($(wc -c < "$DB_FILE") bytes)"
