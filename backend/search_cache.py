"""In-memory TTL caches for search hot paths (embeddings, parse, hybrid results)."""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from threading import Lock


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


# Cache aggressively: a repeated query within the month should never re-hit the
# paid APIs (Gemini parse, Voyage embed), so the $10/month budget stretches far.
# TTL is 30 days; parse/embed caches gate the paid calls so they're the largest.
# embed_cache holds full query vectors (~4KB each at 1024 dims), so it's capped
# more tightly than the string/list caches to bound RAM (~40MB at 10k entries).
CACHE_TTL_SEC = _int_env("SEARCH_CACHE_TTL_SEC", 2592000)   # 30 days
EMBED_CACHE_SIZE = _int_env("EMBED_CACHE_SIZE", 10000)      # query vectors (RAM-heavy)
PARSE_CACHE_SIZE = _int_env("PARSE_CACHE_SIZE", 50000)      # tiny dicts — gates Gemini
HYBRID_CACHE_SIZE = _int_env("HYBRID_CACHE_SIZE", 20000)    # ranked id lists (local)
FTS_CACHE_SIZE = _int_env("FTS_CACHE_SIZE", 20000)          # ranked id lists (local)


class TTLCache:
    """Thread-safe LRU cache with per-entry TTL."""

    def __init__(self, maxsize: int, ttl: int, name: str):
        self.maxsize = maxsize
        self.ttl = ttl
        self.name = name
        self._data: OrderedDict = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key):
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            value, expiry = entry
            if now >= expiry:
                del self._data[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key, value) -> None:
        expiry = time.time() + self.ttl
        with self._lock:
            self._data[key] = (value, expiry)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)


embed_cache = TTLCache(EMBED_CACHE_SIZE, CACHE_TTL_SEC, "embed")
parse_cache = TTLCache(PARSE_CACHE_SIZE, CACHE_TTL_SEC, "parse")
hybrid_cache = TTLCache(HYBRID_CACHE_SIZE, CACHE_TTL_SEC, "hybrid")
fts_cache = TTLCache(FTS_CACHE_SIZE, CACHE_TTL_SEC, "fts")
