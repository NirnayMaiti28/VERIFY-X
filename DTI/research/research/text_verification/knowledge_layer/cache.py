import threading
import time


class TTLCache:
    def __init__(self, ttl_seconds=86400):
        self.ttl_seconds = int(ttl_seconds)
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key):
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None

            expires_at, value = item
            if expires_at <= now:
                self._store.pop(key, None)
                return None

            return value

    def set(self, key, value):
        expires_at = time.time() + self.ttl_seconds
        with self._lock:
            self._store[key] = (expires_at, value)

    def clear(self):
        with self._lock:
            self._store.clear()


__all__ = ["TTLCache"]
