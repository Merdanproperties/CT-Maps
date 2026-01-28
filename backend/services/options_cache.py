"""
In-memory TTL cache for options/autocomplete endpoints (towns, zoning, unit types, owner cities/states).
Reduces repeated heavy DISTINCT queries and prevents timeouts after the first load.
No external services (e.g. Redis) required.
"""
import threading
import time
from typing import Any, Callable, Optional

# Default TTL: 10 minutes. Options data changes infrequently.
DEFAULT_TTL_SECONDS = 600


class OptionsCache:
    """Thread-safe in-memory cache with TTL. Key -> (value, expiry_ts)."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS, max_entries: int = 500):
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()

    def _make_key(self, endpoint: str, **params: Optional[str]) -> str:
        """Build a stable cache key from endpoint name and optional query params."""
        parts = [endpoint]
        for k in sorted(params.keys()):
            v = params.get(k)
            parts.append(f"{k}={v or ''}")
        return "|".join(parts)

    def get(self, endpoint: str, **params: Optional[str]) -> Optional[Any]:
        """Return cached value if present and not expired."""
        key = self._make_key(endpoint, **params)
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            value, expiry = entry
            if time.monotonic() > expiry:
                del self._store[key]
                return None
            return value

    def set(self, endpoint: str, value: Any, **params: Optional[str]) -> None:
        """Store value with TTL. Evict oldest entries if over max_entries."""
        key = self._make_key(endpoint, **params)
        expiry = time.monotonic() + self._ttl
        with self._lock:
            if len(self._store) >= self._max_entries and key not in self._store:
                # Evict oldest by expiry
                oldest = min(self._store.items(), key=lambda x: x[1][1])
                del self._store[oldest[0]]
            self._store[key] = (value, expiry)

    def get_or_compute(
        self,
        endpoint: str,
        compute: Callable[[], Any],
        **params: Optional[str],
    ) -> Any:
        """Return cached value or call compute(), cache result, and return it."""
        cached = self.get(endpoint, **params)
        if cached is not None:
            return cached
        value = compute()
        self.set(endpoint, value, **params)
        return value


# Singleton used by routes
options_cache = OptionsCache(ttl_seconds=DEFAULT_TTL_SECONDS)
