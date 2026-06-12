#!/bin/bash
# Store API keys + R2 credentials in macOS Keychain.
# Run this yourself in Terminal.
# Do NOT run through Cursor, Claude, or paste keys into chat.
#
# Press Enter to skip any prompt — only the values you type are stored.
# Account names here must match _KEYCHAIN_ACCOUNTS in load_secrets.py.
set -euo pipefail

SERVICE="ask-the-early-church"

# store <account> <value> — write to Keychain only if a value was given.
store() {
  local account="$1" value="$2"
  if [ -n "$value" ]; then
    security add-generic-password -U -s "$SERVICE" -a "$account" -w "$value"
    echo "  saved: $account"
  else
    echo "  skipped: $account (no value entered)"
  fi
}

echo "Enter the keys you have; press Enter to skip the rest."
echo

read -r -s -p "Gemini API key   (query parsing): "        GEMINI;  echo
read -r -s -p "Voyage API key   (semantic search): "      VOYAGE;  echo
read -r -s -p "Groq API key     (parser fallback, opt): " GROQ;    echo
read -r -s -p "Anthropic API key(synthesis, disabled): "  ANTHROPIC; echo
read -r    -p "R2 Account ID    (deploy, opt): "           R2_ACCOUNT_ID
read -r    -p "R2 Bucket name   (deploy, opt): "           R2_BUCKET
read -r -s -p "R2 Access Key ID (deploy, opt): "           R2_ACCESS_KEY_ID; echo
read -r -s -p "R2 Secret Access Key (deploy, opt): "       R2_SECRET_ACCESS_KEY; echo

echo
store "gemini"               "$GEMINI"
store "voyage"               "$VOYAGE"
store "groq"                 "$GROQ"
store "anthropic"            "$ANTHROPIC"
store "r2-account-id"        "$R2_ACCOUNT_ID"
store "r2-bucket"            "$R2_BUCKET"
store "r2-access-key-id"     "$R2_ACCESS_KEY_ID"
store "r2-secret-access-key" "$R2_SECRET_ACCESS_KEY"

unset GEMINI VOYAGE GROQ ANTHROPIC R2_ACCOUNT_ID R2_BUCKET R2_ACCESS_KEY_ID R2_SECRET_ACCESS_KEY

echo
echo "Done. Credentials saved to Keychain (service: $SERVICE)."
echo "If you keep any plain-text copy, remove it:"
echo "  rm -f ~/.secrets/ask-the-early-church.env"
