"""Load secrets for the backend.

API keys (Anthropic, Voyage) are read from macOS Keychain when available —
they never need to live in a plain-text file. Non-sensitive config
(ALLOWED_ORIGIN, cache tuning, etc.) can live in:

    ~/.secrets/ask-the-early-church.env

Override that path with ASK_THE_EARLY_CHURCH_SECRETS.
"""

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

KEYCHAIN_SERVICE = "ask-the-early-church"
DEFAULT_SECRETS_PATH = Path.home() / ".secrets" / "ask-the-early-church.env"

_KEYCHAIN_ACCOUNTS = {
    "GEMINI_API_KEY": "gemini",        # primary query parser (Gemini 2.5 Flash)
    "VOYAGE_API_KEY": "voyage",        # semantic-search embeddings
    "GROQ_API_KEY": "groq",            # fallback query parser (Llama 3.3 70B)
    "ANTHROPIC_API_KEY": "anthropic",  # Claude synthesis (currently disabled)
}


def secrets_path() -> Path:
    override = os.getenv("ASK_THE_EARLY_CHURCH_SECRETS", "").strip()
    return Path(override).expanduser() if override else DEFAULT_SECRETS_PATH


def _keychain_get(account: str) -> str | None:
    try:
        result = subprocess.run(
            [
                "security", "find-generic-password",
                "-s", KEYCHAIN_SERVICE,
                "-a", account,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            return value or None
    except (FileNotFoundError, OSError):
        pass
    return None


def _load_api_keys_from_keychain() -> None:
    for env_name, account in _KEYCHAIN_ACCOUNTS.items():
        if os.getenv(env_name):
            continue
        value = _keychain_get(account)
        if value:
            os.environ[env_name] = value


def load_secrets() -> Path | None:
    _load_api_keys_from_keychain()
    path = secrets_path()
    if path.is_file():
        # Keychain values win; file supplies non-key config only.
        load_dotenv(path, override=False)
    return path if path.is_file() else None
