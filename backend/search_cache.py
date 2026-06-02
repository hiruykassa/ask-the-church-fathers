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


CACHE_TTL_SEC = _int_env("SEARCH_CACHE_TTL_SEC", 3600)
EMBED_CACHE_SIZE = _int_env("EMBED_CACHE_SIZE", 1024)
PARSE_CACHE_SIZE = _int_env("PARSE_CACHE_SIZE", 512)
HYBRID_CACHE_SIZE = _int_env("HYBRID_CACHE_SIZE", 512)
FTS_CACHE_SIZE = _int_env("FTS_CACHE_SIZE", 512)


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
