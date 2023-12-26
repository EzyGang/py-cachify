from __future__ import annotations

import pickle
from typing import Any, Union

from py_cachify.backend.clients import AsyncWrapper, MemoryCache
from py_cachify.backend.exceptions import CachifyInitError
from py_cachify.backend.types import AsyncClient, SyncClient


class Cachify:
    def __init__(
        self, sync_client: Union[SyncClient, MemoryCache], async_client: Union[AsyncClient, AsyncWrapper], prefix: str
    ) -> None:
        self._sync_client = sync_client
        self._async_client = async_client
        self._prefix = prefix

    def set(self, key: str, val: Any, ttl: Union[int, None] = None) -> Any:
        self._sync_client.set(name=f'{self._prefix}{key}', value=pickle.dumps(val), ex=ttl)

    def get(self, key: str) -> Any:
        return (val := self._sync_client.get(name=f'{self._prefix}{key}')) and pickle.loads(val)

    def delete(self, key: str) -> Any:
        return self._sync_client.delete(f'{self._prefix}{key}')

    async def a_get(self, key: str) -> Any:
        return (val := await self._async_client.get(name=f'{self._prefix}{key}')) and pickle.loads(val)

    async def a_set(self, key: str, val: Any, ttl: Union[int, None] = None) -> Any:
        await self._async_client.set(name=f'{self._prefix}{key}', value=pickle.dumps(val), ex=ttl)

    async def a_delete(self, key: str) -> Any:
        return await self._async_client.delete(f'{self._prefix}{key}')


_cachify: Cachify | None = None


def init_cachify(
    sync_client: SyncClient = (mc := MemoryCache()),
    async_client: AsyncClient = AsyncWrapper(cache=mc),
    prefix: str = '_PYC_',
) -> None:
    global _cachify
    _cachify = Cachify(sync_client=sync_client, async_client=async_client, prefix=prefix)


def get_cachify() -> Cachify:
    global _cachify
    if _cachify is None:
        raise CachifyInitError('Cachify is not initialized, did you forget to call `init_cachify`?')

    return _cachify
