#!/usr/bin/env bash
# Upload database.db to Cloudflare R2.
# Credentials are read from macOS Keychain — no env vars needed.
#
# Usage:
#   cd ~/ask-the-early-church/backend
#   bash upload_db_to_r2.sh
#
# First time? Run store_keys_in_keychain.sh to save your R2 credentials.

set -euo pipefail

SERVICE="ask-the-early-church"
DB_FILE="${DB_FILE:-database.db}"
OBJECT_KEY="${R2_OBJECT_KEY:-database.db}"

# ── Read credentials from Keychain ───────────────────────────────────────────
keychain_get() {
  security find-generic-password -s "$SERVICE" -a "$1" -w 2>/dev/null || true
}

R2_ACCOUNT_ID="${R2_ACCOUNT_ID:-$(keychain_get r2-account-id)}"
R2_BUCKET="${R2_BUCKET:-$(keychain_get r2-bucket)}"
R2_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID:-$(keychain_get r2-access-key-id)}"
R2_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY:-$(keychain_get r2-secret-access-key)}"

# ── Validate ──────────────────────────────────────────────────────────────────
missing=()
[[ -z "$R2_ACCOUNT_ID"        ]] && missing+=("r2-account-id")
[[ -z "$R2_BUCKET"            ]] && missing+=("r2-bucket")
[[ -z "$R2_ACCESS_KEY_ID"     ]] && missing+=("r2-access-key-id")
[[ -z "$R2_SECRET_ACCESS_KEY" ]] && missing+=("r2-secret-access-key")

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "ERROR: missing Keychain entries: ${missing[*]}" >&2
  echo "Run:  bash store_keys_in_keychain.sh" >&2
  exit 1
fi

if [[ ! -f "$DB_FILE" ]]; then
  echo "ERROR: $DB_FILE not found. Run from the backend/ directory." >&2
  exit 1
fi

SIZE=$(wc -c < "$DB_FILE" | tr -d ' ')
echo "[upload] Uploading $DB_FILE ($SIZE bytes) -> r2://$R2_BUCKET/$OBJECT_KEY"

# ── Upload via Python (boto3) ─────────────────────────────────────────────────
R2_ACCOUNT_ID="$R2_ACCOUNT_ID" \
R2_BUCKET="$R2_BUCKET" \
R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
OBJECT_KEY="$OBJECT_KEY" \
DB_FILE="$DB_FILE" \
python3 - <<'PYEOF'
import boto3, os, sys

endpoint = f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
)

try:
    s3.upload_file(
        os.environ["DB_FILE"],
        os.environ["R2_BUCKET"],
        os.environ["OBJECT_KEY"],
        ExtraArgs={"ContentType": "application/octet-stream"},
    )
    print(f"[upload] Done -> r2://{os.environ['R2_BUCKET']}/{os.environ['OBJECT_KEY']}")
except Exception as e:
    print(f"[upload] FAILED: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF

echo "[upload] Complete. Redeploy on Render to pick up the new database (prestart.sh re-fetches DB_URL on a fresh container)."
