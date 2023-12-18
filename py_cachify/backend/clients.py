from __future__ import annotations

import time
from typing import Any, Dict, Tuple, Union


class MemoryCache:
    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[Any, Union[float, None]]] = {}

    def set(self, name: str, value: Any, ex: Union[int, None] = None) -> None:
        self._cache[name] = value, ex and time.time() + ex

    def get(self, name: str, default: Any = None) -> Any:
        val, exp_at = self._cache.get(name, (default, None))

        if not exp_at or exp_at > time.time():
            return val

        self.delete(name)
        return default

    def delete(self, *names: str) -> None:
        for key in names:
            if key not in self._cache:
                continue

            del self._cache[key]


class AsyncWrapper:
    def __init__(self, cache: MemoryCache) -> None:
        self._cache = cache

    async def get(self, name: str, default: Any = None) -> Any:
        return self._cache.get(name=name, default=default)

    async def delete(self, *names: str) -> Any:
        self._cache.delete(*names)

    async def set(self, name: str, value: Any, ex: Union[int, None] = None) -> Any:
        self._cache.set(name=name, value=value, ex=ex)
