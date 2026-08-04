"""Cost + latency telemetry and a monthly API budget cap.

Two responsibilities:

1. ``log_ai_call`` — emit a structured JSON line for every Voyage/Anthropic
   call so we can grep spend, latency, and error rate from Render logs (or
   CloudWatch on AWS).

2. ``budget_remaining`` / ``record_spend`` — a Redis-backed monthly counter
   that lets the search path fall back to FTS-only once we hit the budget
   cap. Protects the Gemini/Voyage credit card from runaway abuse.

All Redis access goes through ``RATELIMIT_STORAGE_URI`` (the same URL used
by flask-limiter), so a single env var configures both. If Redis is
unreachable the budget check fails *open* — we'd rather serve a query than
500 because the spend counter is down.
"""

import json
import logging
import os
import time

log = logging.getLogger(__name__)

# Hard MONTHLY ceiling: $10/month. Once this calendar month's spend crosses it,
# search degrades to keyword-only (FTS) for the rest of the month, then resets on
# the 1st. Override via env. NOTE: the cap only bites when RATELIMIT_STORAGE_URI
# (Redis) is configured — without it the counter has nowhere to live and fails
# open (so spend is unbounded; rely on heavy caching to keep it small).
_DEFAULT_MONTHLY_BUDGET_USD = 10.0


def _budget_from_env() -> float:
    """Read the cap, falling back on garbage rather than refusing to boot.

    This runs at import time, so raising here means the container never starts —
    a typo in an env var would take the whole site down to protect a $10 ceiling.
    Mirrors ``_positive_int_env`` in app.py, which guards the same class of
    mistake for the cache TTLs.
    """
    raw = os.getenv("MONTHLY_API_BUDGET_USD")
    if raw is None or not raw.strip():
        return _DEFAULT_MONTHLY_BUDGET_USD
    try:
        value = float(raw)
    except (TypeError, ValueError):
        log.warning(
            "MONTHLY_API_BUDGET_USD is not a number (%r) — using default $%s",
            raw, _DEFAULT_MONTHLY_BUDGET_USD,
        )
        return _DEFAULT_MONTHLY_BUDGET_USD
    if value < 0:
        log.warning(
            "MONTHLY_API_BUDGET_USD is negative (%s) — using default $%s",
            value, _DEFAULT_MONTHLY_BUDGET_USD,
        )
        return _DEFAULT_MONTHLY_BUDGET_USD
    return value


MONTHLY_BUDGET_USD = _budget_from_env()
_REDIS_URL = os.getenv("RATELIMIT_STORAGE_URI", "").strip()

# Approximate $/call — tune as model pricing changes. These are pessimistic
# so the cap trips a little early rather than a little late.
COST_PER_CALL_USD = {
    "voyage_embed": 0.000002,   # voyage-3 ($0.06/1M) — query is ~15 tokens
    "anthropic_parse": 0.0005,  # Haiku — small prompt, cached system (disabled)
    "gemini_parse": 0.00015,    # Gemini 2.5 Flash-Lite + author roster (~1,350 in / 20 out)
    "groq_parse": 0.0,          # Groq Llama 3.3 70B free tier
}

_redis = None
if _REDIS_URL and _REDIS_URL.startswith(("redis://", "rediss://")):
    try:
        import redis  # noqa: WPS433 — optional dep, only imported when configured
        _redis = redis.from_url(_REDIS_URL, socket_timeout=2)
    except Exception as exc:
        log.warning("telemetry: redis init failed (%s); budget cap disabled", exc)
        _redis = None


def _period_key() -> str:
    # One counter per calendar month — resets automatically on the 1st.
    return f"aetc:spend:{time.strftime('%Y-%m')}"


def budget_remaining() -> bool:
    """True if this month's spend is still under MONTHLY_BUDGET_USD.

    Fails *open* on any Redis error — we don't want a flaky cache to break
    search. The flip side: a sustained Redis outage disables the cap.
    """
    if _redis is None:
        return True
    try:
        spent = float(_redis.get(_period_key()) or 0)
        return spent < MONTHLY_BUDGET_USD
    except Exception as exc:
        log.warning("telemetry: budget read failed (%s); allowing call", exc)
        return True


def budget_status() -> dict:
    """Snapshot for the health endpoint: whether the monthly cap is actually
    enforced (Redis reachable) and how much has been spent this month."""
    enabled = _redis is not None
    spent = None
    if enabled:
        try:
            spent = round(float(_redis.get(_period_key()) or 0), 4)
        except Exception:
            spent = None
    return {"enabled": enabled, "spent_usd": spent, "limit_usd": MONTHLY_BUDGET_USD}


def record_spend(call_type: str) -> None:
    """Increment this month's spend counter by the cost-per-call for ``call_type``."""
    if _redis is None:
        return
    cost = COST_PER_CALL_USD.get(call_type, 0.0)
    if cost == 0.0:
        return
    try:
        key = _period_key()
        pipe = _redis.pipeline()
        pipe.incrbyfloat(key, cost)
        pipe.expire(key, 3456000)  # keep ~40 days so the month's counter outlives the month
        pipe.execute()
    except Exception as exc:
        log.warning("telemetry: spend record failed (%s)", exc)


def log_ai_call(
    provider: str,
    model: str,
    latency_ms: float,
    ok: bool,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    error: str | None = None,
) -> None:
    """One structured JSON line per AI call — grepable in any log backend."""
    payload = {
        "event": "ai_call",
        "provider": provider,
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "ok": ok,
    }
    if tokens_in is not None:
        payload["tokens_in"] = tokens_in
    if tokens_out is not None:
        payload["tokens_out"] = tokens_out
    if error:
        payload["error"] = error
    log.info(json.dumps(payload))
