import threading
import time
from typing import Any, Optional, Union


class MemoryCache:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, Union[float, None]]] = {}
        self._lock = threading.RLock()

    def set(self, name: str, value: Any, ex: Union[int, None] = None, nx: bool = False) -> Optional[bool]:
        """
        Set a value with optional NX semantics.

        - If nx is False: behaves like a normal set, always overwriting the value.
          Returns None to mirror the fact that some backends don't return a meaningful value.
        - If nx is True: only set the value if the key is absent or expired.
          Returns True if the value was set, False if the key already exists and is not expired.
        """
        if not nx:
            self._cache[name] = value, ex and time.time() + ex
            return None

        # NX path: need atomic check+set
        with self._lock:
            existing = self._cache.get(name)
            if existing is not None:
                _, exp_at = existing
                if exp_at is None or exp_at > time.time():
                    return False

            self._cache[name] = value, ex and time.time() + ex
            return True

    def get(self, name: str) -> Optional[Any]:
        val, exp_at = self._cache.get(name, (None, None))
        if not exp_at or exp_at > time.time():
            return val

        self.delete(name)
        return None

    def delete(self, *names: str) -> None:
        for key in names:
            if key not in self._cache:
                continue

            del self._cache[key]


class AsyncWrapper:
    def __init__(self, cache: MemoryCache) -> None:
        self._cache = cache

    async def get(self, name: str) -> Optional[Any]:
        return self._cache.get(name=name)

    async def delete(self, *names: str) -> Any:
        self._cache.delete(*names)

    async def set(self, name: str, value: Any, ex: Union[int, None] = None, nx: bool = False) -> Optional[Any]:
        return self._cache.set(name=name, value=value, ex=ex, nx=nx)
