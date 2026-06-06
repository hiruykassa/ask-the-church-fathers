"""Cost + latency telemetry and a daily API budget cap.

Two responsibilities:

1. ``log_ai_call`` — emit a structured JSON line for every Voyage/Anthropic
   call so we can grep spend, latency, and error rate from Render logs (or
   CloudWatch on AWS).

2. ``budget_remaining`` / ``record_spend`` — a Redis-backed daily counter
   that lets the search path fall back to FTS-only once we hit the budget
   cap. Protects the Anthropic/Voyage credit card from runaway abuse.

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

DAILY_BUDGET_USD = float(os.getenv("DAILY_API_BUDGET_USD", "5"))
_REDIS_URL = os.getenv("RATELIMIT_STORAGE_URI", "").strip()

# Approximate $/call — tune as model pricing changes. These are pessimistic
# so the cap trips a little early rather than a little late.
COST_PER_CALL_USD = {
    "voyage_embed": 0.0001,   # voyage-3 — short query
    "anthropic_parse": 0.0005,  # Haiku — small prompt, cached system (disabled)
    "gemini_parse": 0.0,        # Gemini 2.5 Flash free tier
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


def _today_key() -> str:
    return f"aetc:spend:{time.strftime('%Y-%m-%d')}"


def budget_remaining() -> bool:
    """True if today's spend is still under DAILY_BUDGET_USD.

    Fails *open* on any Redis error — we don't want a flaky cache to break
    search. The flip side: a sustained Redis outage disables the cap.
    """
    if _redis is None:
        return True
    try:
        spent = float(_redis.get(_today_key()) or 0)
        return spent < DAILY_BUDGET_USD
    except Exception as exc:
        log.warning("telemetry: budget read failed (%s); allowing call", exc)
        return True


def record_spend(call_type: str) -> None:
    """Increment today's spend counter by the cost-per-call for ``call_type``."""
    if _redis is None:
        return
    cost = COST_PER_CALL_USD.get(call_type, 0.0)
    if cost == 0.0:
        return
    try:
        key = _today_key()
        pipe = _redis.pipeline()
        pipe.incrbyfloat(key, cost)
        pipe.expire(key, 172800)  # keep 2 days for debugging
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
