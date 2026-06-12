#!/usr/bin/env bash
# Verify R2 credentials are in Keychain AND actually work — without printing them.
# Run this yourself in Terminal before uploading:
#   cd ~/ask-the-early-church/backend && bash verify_r2.sh
#
# It checks each Keychain entry exists, then does a read-only head_bucket /
# list against R2. Secret values are never echoed.

set -euo pipefail

SERVICE="ask-the-early-church"
OBJECT_KEY="${R2_OBJECT_KEY:-database.db}"

keychain_get() { security find-generic-password -s "$SERVICE" -a "$1" -w 2>/dev/null || true; }

R2_ACCOUNT_ID="$(keychain_get r2-account-id)"
R2_BUCKET="$(keychain_get r2-bucket)"
R2_ACCESS_KEY_ID="$(keychain_get r2-access-key-id)"
R2_SECRET_ACCESS_KEY="$(keychain_get r2-secret-access-key)"

echo "Keychain entries (presence only):"
ok=1
for name in r2-account-id r2-bucket r2-access-key-id r2-secret-access-key; do
  val="$(keychain_get "$name")"
  if [ -n "$val" ]; then echo "  ✓ $name"; else echo "  ✗ $name  (missing)"; ok=0; fi
done
if [ "$ok" -ne 1 ]; then
  echo "Run: bash store_keys_in_keychain.sh" >&2
  exit 1
fi

echo
echo "Testing R2 connectivity (read-only)…"
R2_ACCOUNT_ID="$R2_ACCOUNT_ID" R2_BUCKET="$R2_BUCKET" \
R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
OBJECT_KEY="$OBJECT_KEY" \
python3 - <<'PYEOF'
import os, sys
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("  ✗ boto3 not installed. Run: pip install boto3", file=sys.stderr)
    sys.exit(2)

endpoint = f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com"
s3 = boto3.client("s3", endpoint_url=endpoint,
                  aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                  region_name="auto")
bucket = os.environ["R2_BUCKET"]
try:
    s3.head_bucket(Bucket=bucket)
    print(f"  ✓ credentials valid, bucket '{bucket}' reachable")
except ClientError as e:
    code = e.response.get("Error", {}).get("Code", "?")
    print(f"  ✗ cannot access bucket '{bucket}': {code}", file=sys.stderr)
    print("    (check Account ID, bucket name, and that the token has access to this bucket)", file=sys.stderr)
    sys.exit(1)

# Is the DB already uploaded?
try:
    h = s3.head_object(Bucket=bucket, Key=os.environ["OBJECT_KEY"])
    print(f"  • '{os.environ['OBJECT_KEY']}' already in bucket ({h['ContentLength']} bytes)")
except ClientError:
    print(f"  • '{os.environ['OBJECT_KEY']}' not uploaded yet — run: bash upload_db_to_r2.sh")
PYEOF

echo
echo "Done."
