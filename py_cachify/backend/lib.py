from typing import Any

from py_cachify.backend.clients import AsyncWrapper, MemoryCache
from py_cachify.backend.exceptions import CachifyInitError
from py_cachify.backend.types import AsyncClient, SyncClient


class Cachify:
    def __init__(self, sync_client: SyncClient | MemoryCache, async_client: AsyncClient | AsyncWrapper) -> None:
        self._sync_client = sync_client
        self._async_client = async_client

    def set(self, key: str, val: Any, ttl: int | None = None) -> Any:
        self._sync_client.set(name=key, value=val, ex=ttl)

    def get(self, key: str) -> Any:
        return self._sync_client.get(name=key)

    def delete(self, key: str) -> Any:
        return self._sync_client.delete(key)

    async def a_get(self, key: str) -> Any:
        return await self._async_client.get(name=key)

    async def a_set(self, key: str, val: Any, ttl: int | None = None) -> Any:
        await self._async_client.set(name=key, value=val, ex=ttl)

    async def a_delete(self, key: str) -> Any:
        return await self._async_client.delete(key)


_cachify: Cachify | None = None


def init_cachify(
    sync_client: SyncClient = (mc := MemoryCache()), async_client: AsyncClient = AsyncWrapper(cache=mc)
) -> None:
    global _cachify
    _cachify = Cachify(sync_client=sync_client, async_client=async_client)


def get_cachify() -> Cachify:
    global _cachify
    if _cachify is None:
        raise CachifyInitError('Cachify is not initialized, did you forget to call `init_cachify`?')

    return _cachify
