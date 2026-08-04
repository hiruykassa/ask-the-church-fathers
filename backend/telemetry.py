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
from threading import Lock

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


# In-process fallback counter, used when Redis is not configured.
#
# Previously the cap simply did not exist without Redis: budget_remaining()
# returned True unconditionally, so MONTHLY_API_BUDGET_USD was decorative and
# spend was bounded only by caching. A per-process counter is weaker than a
# shared one — with N gunicorn workers the effective ceiling is N x the limit,
# and it resets when the instance restarts — but "approximately enforced" beats
# "not enforced", and it needs no infrastructure.
_local_spend: dict[str, float] = {}
_local_lock = Lock()


def _local_spent() -> float:
    with _local_lock:
        return _local_spend.get(_period_key(), 0.0)


def budget_remaining() -> bool:
    """True if this month's spend is still under MONTHLY_BUDGET_USD.

    Fails *open* on any Redis error — we don't want a flaky cache to break
    search. The flip side: a sustained Redis outage falls back to the
    in-process counter, which under-counts across workers.
    """
    if _redis is None:
        return _local_spent() < MONTHLY_BUDGET_USD
    try:
        spent = float(_redis.get(_period_key()) or 0)
        return spent < MONTHLY_BUDGET_USD
    except Exception as exc:
        log.warning("telemetry: budget read failed (%s); using in-process count", exc)
        return _local_spent() < MONTHLY_BUDGET_USD


def budget_status() -> dict:
    """Snapshot for the health endpoint.

    ``scope`` says how much the cap is worth: "shared" means one counter across
    every worker and instance; "process" means each worker counts separately, so
    the real ceiling is roughly N x limit and resets on restart. The cap is
    always enforced now — ``enabled`` is kept for compatibility and mirrors
    whether the counter is shared.
    """
    shared = _redis is not None
    spent = None
    if shared:
        try:
            spent = round(float(_redis.get(_period_key()) or 0), 4)
        except Exception:
            spent = None
    if spent is None:
        spent = round(_local_spent(), 6)
    return {
        "enabled": shared,
        "scope": "shared" if shared else "process",
        "spent_usd": spent,
        "limit_usd": MONTHLY_BUDGET_USD,
    }


def record_spend(call_type: str) -> None:
    """Increment this month's spend counter by the cost-per-call for ``call_type``."""
    cost = COST_PER_CALL_USD.get(call_type, 0.0)
    if cost == 0.0:
        return

    # Always count locally, Redis or not: it is the fallback budget_remaining()
    # reads, and it keeps /api/health honest about spend on a single instance.
    key = _period_key()
    with _local_lock:
        _local_spend[key] = _local_spend.get(key, 0.0) + cost
        # One entry per month; drop anything older so this cannot grow.
        for stale in [k for k in _local_spend if k != key]:
            del _local_spend[stale]

    if _redis is None:
        return
    try:
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
