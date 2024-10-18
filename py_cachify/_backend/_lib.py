import pickle
from typing import Any, Optional, Union

from ._clients import AsyncWrapper, MemoryCache
from ._exceptions import CachifyInitError
from ._types._common import AsyncClient, SyncClient


class Cachify:
    def __init__(
        self,
        sync_client: Union[SyncClient, MemoryCache],
        async_client: Union[AsyncClient, AsyncWrapper],
        default_expiration: Optional[int],
        prefix: str,
    ) -> None:
        self._sync_client = sync_client
        self._async_client = async_client
        self._prefix = prefix
        self.default_expiration = default_expiration

    def set(self, key: str, val: Any, ttl: Union[int, None] = None) -> Any:
        _ = self._sync_client.set(name=f'{self._prefix}{key}', value=pickle.dumps(val), ex=ttl)

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


_cachify: Optional[Cachify] = None
_mc = MemoryCache()
_amc = AsyncWrapper(_mc)


def init_cachify(
    sync_client: SyncClient = _mc,
    async_client: AsyncClient = _amc,
    default_lock_expiration: Optional[int] = 30,
    prefix: str = 'PYC-',
) -> None:
    """
    Initialize the Cachify instance with the specified clients and settings.

    Args:
    sync_client (Union[SyncClient, MemoryCache], optional): The synchronous client to use.
        Defaults to MemoryCache().
    async_client (Union[AsyncClient, AsyncWrapper], optional): The asynchronous client to use.
        Defaults to AsyncWrapper(cache=MemoryCache()).
    default_lock_expiration (Optional[int], optional): The default expiration time for locks.
        Defaults to 30.
    prefix (str, optional): The prefix to use for keys. Defaults to 'PYC-'.
    """

    global _cachify
    _cachify = Cachify(
        sync_client=sync_client, async_client=async_client, prefix=prefix, default_expiration=default_lock_expiration
    )


def get_cachify() -> Cachify:
    global _cachify
    if _cachify is None:
        raise CachifyInitError('Cachify is not initialized, did you forget to call `init_cachify`?')

    return _cachify
