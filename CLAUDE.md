# Claude / Cowork instructions

## Secrets — strict

Never read, print, or request API keys.

**Do not:**

- Read `~/.secrets/`, `backend/.env`, or any env file that may hold credentials
- Run `security find-generic-password`, `cat` on secret paths, or `env`/`printenv` to extract keys
- Ask the user to paste `ANTHROPIC_API_KEY` or `VOYAGE_API_KEY` into chat

**Allowed:**

- `backend/.env.example` (template only)
- Code changes to `load_secrets.py` / `store_keys_in_keychain.sh` without running them with real keys
- Instruct the user to run `bash backend/store_keys_in_keychain.sh` in their own Terminal

**Key storage:**

- Local API keys: macOS Keychain (`ask-the-early-church`)
- Non-sensitive config: `~/.secrets/ask-the-early-church.env`
- Production: platform secret env vars only

## Project

Flask backend (`backend/`) + Vite React frontend (`src/`). Secrets load via `backend/load_secrets.py`.
