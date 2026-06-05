#!/bin/bash
# Store API keys in macOS Keychain — run this yourself in Terminal.
# Do NOT run through Cursor, Claude, or paste keys into chat.
set -euo pipefail

SERVICE="ask-the-early-church"

read -r -s -p "Anthropic API key: " ANTHROPIC
echo
read -r -s -p "Voyage API key: " VOYAGE
echo

security add-generic-password -U -s "$SERVICE" -a "anthropic" -w "$ANTHROPIC"
security add-generic-password -U -s "$SERVICE" -a "voyage" -w "$VOYAGE"

unset ANTHROPIC VOYAGE

echo "Done. Keys are in Keychain (service: $SERVICE)."
echo "Remove any plain-text copy:"
echo "  rm -f ~/.secrets/ask-the-early-church.env"
