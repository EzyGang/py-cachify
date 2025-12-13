import pickle
from typing import TYPE_CHECKING, Any, Optional, Union

from ._clients import AsyncWrapper, MemoryCache
from ._exceptions import CachifyInitError
from ._types._common import UNSET, AsyncClient, Decoder, Encoder, SyncClient, UnsetType
from ._types._lock_wrap import WrappedFunctionLock
from ._types._reset_wrap import WrappedFunctionReset


if TYPE_CHECKING:
    from ._lock import lock as _lock_cls


class CachifyClient:
    def __init__(
        self,
        sync_client: SyncClient,
        async_client: AsyncClient,
        default_expiration: Optional[int],
        prefix: str,
        default_cache_ttl: Optional[int] = None,
    ) -> None:
        self._sync_client = sync_client
        self._async_client = async_client
        self._prefix = prefix
        self.default_expiration = default_expiration
        self.default_cache_ttl = default_cache_ttl

    def set(self, key: str, val: Any, ttl: Union[int, None] = None) -> Any:
        _ = self._sync_client.set(name=f'{self._prefix}{key}', value=pickle.dumps(val), ex=ttl, nx=False)

    def get(self, key: str) -> Any:
        return (val := self._sync_client.get(name=f'{self._prefix}{key}')) and pickle.loads(val)

    def delete(self, key: str) -> Any:
        return self._sync_client.delete(f'{self._prefix}{key}')

    def try_acquire_lock(self, key: str, ttl: Optional[int]) -> bool:
        """
        Returns True if the lock was acquired, False if it is already held.
        """
        name = f'{self._prefix}{key}'
        payload = pickle.dumps(1)
        res = self._sync_client.set(name=name, value=payload, ex=ttl, nx=True)
        return bool(res)

    async def a_get(self, key: str) -> Any:
        return (val := await self._async_client.get(name=f'{self._prefix}{key}')) and pickle.loads(val)

    async def a_set(self, key: str, val: Any, ttl: Union[int, None] = None) -> Any:
        await self._async_client.set(name=f'{self._prefix}{key}', value=pickle.dumps(val), ex=ttl, nx=False)

    async def a_delete(self, key: str) -> Any:
        return await self._async_client.delete(f'{self._prefix}{key}')

    async def a_try_acquire_lock(self, key: str, ttl: Optional[int]) -> bool:
        """
        Returns True if the lock was acquired, False if it is already held.
        """
        name = f'{self._prefix}{key}'
        payload = pickle.dumps(1)
        res = await self._async_client.set(name=name, value=payload, ex=ttl, nx=True)
        return bool(res)


_cachify: Optional['CachifyClient'] = None


class Cachify:
    """
    High-level interface that exposes decorator factories bound to a dedicated CachifyClient.

    This class is intentionally a thin wrapper around the top-level `cached`, `lock`,
    and `once` APIs. It only manages `_current_client` while delegating to those
    functions so that their signatures and behavior remain intact.
    """

    def __init__(
        self,
        sync_client: SyncClient,
        async_client: AsyncClient,
        prefix: str,
        default_expiration: Optional[int],
        default_cache_ttl: Optional[int],
    ) -> None:
        self._client = CachifyClient(
            sync_client=sync_client,
            async_client=async_client,
            default_expiration=default_expiration,
            default_cache_ttl=default_cache_ttl,
            prefix=prefix,
        )

    def cached(
        self,
        key: str,
        ttl: Union[Optional[int], UnsetType] = UNSET,
        enc_dec: Union[tuple[Encoder, Decoder], None] = None,
    ) -> WrappedFunctionReset:
        """
        Decorator that caches the result of a function based on the specified key, time-to-live (ttl),
            and encoding/decoding functions.

        Args:
        key (str): The key used to identify the cached result, could be a format string.
        ttl (Union[int, None, UnsetType], optional): The time-to-live for the cached result.
            If UNSET (default), default_cache_ttl from cachify client is used.
            If None, means indefinitely.
        enc_dec (Union[Tuple[Encoder, Decoder], None], optional): The encoding and decoding functions for
          the cached value.
            Defaults to None.

        Returns:
        WrappedFunctionReset: Either a synchronous or asynchronous function with reset method attached to it,
        reset(*args, **kwargs) matches the type of original function, accepts the same argument,
            and could be used to reset the cache.
        """
        from ._cached import _cached_impl  # pyright: ignore[reportPrivateUsage]

        return _cached_impl(key=key, ttl=ttl, enc_dec=enc_dec, client_provider=lambda: self._client)

    def lock(
        self,
        key: str,
        nowait: bool = True,
        timeout: Optional[Union[int, float]] = None,
        exp: Union[Optional[int], UnsetType] = UNSET,
    ) -> '_lock_cls':
        """
        Class to manage locking mechanism for synchronous and asynchronous functions.

        Args:
        key (str): The key used to identify the lock.
        nowait (bool, optional): If True, do not wait for the lock to be released. Defaults to True.
        timeout (Union[int, float], optional): The time in seconds to wait for the lock if nowait is False.
            Defaults to None.
        exp (Union[int, None], optional): The expiration time for the lock.
            Defaults to UNSET and global value from cachify is used in that case.

        Methods:
        __enter__: Acquire a lock for the specified key, synchronous.
        is_locked: Check if the lock is currently held, synchronous.
        release: Release the lock that is being held.

        __aenter__: Async version of __enter__ to acquire a lock for the specified key.
        is_alocked: Check if the lock is currently held asynchronously.
        arelease: Release the lock that is being held asynchronously.

        __call__: Decorator to acquire a lock for the wrapped function and handle synchronization
            for synchronous and asynchronous functions.
            Attaches method `is_locked(*args, **kwargs)` to a wrapped function to quickly check if it's locked.
        """
        from ._lock import lock as _lock

        lk = _lock(key=key, nowait=nowait, timeout=timeout, exp=exp)

        lk._cachify = self._client  # pyright: ignore[reportPrivateUsage]

        return lk

    def once(self, key: str, raise_on_locked: bool = False, return_on_locked: Any = None) -> WrappedFunctionLock:
        """
        Decorator that ensures a function is only called once at a time,
            based on a specified key (could be a format string).

        Args:
        key (str): The key used to identify the lock.
            Required.
        raise_on_locked (bool, optional): If True, raise an exception when the function is already locked.
            Defaults to False.
        return_on_locked (Any, optional): The value to return when the function is already locked.
            Defaults to None.

        Returns:
        SyncOrAsyncRelease: Either a synchronous or asynchronous wrapped function with `release` and `is_locked`
            methods attached to it.
        """
        from ._lock import _once_impl  # pyright: ignore[reportPrivateUsage]

        return _once_impl(
            key=key,
            raise_on_locked=raise_on_locked,
            return_on_locked=return_on_locked,
            client_provider=lambda: self._client,
        )


def init_cachify(
    sync_client: Optional[SyncClient] = None,
    async_client: Optional[AsyncClient] = None,
    default_lock_expiration: Optional[int] = 30,
    default_cache_ttl: Optional[int] = None,
    prefix: str = 'PYC-',
    *,
    is_global: bool = True,
) -> Cachify:
    """
    Initialize the Cachify client with the specified clients and settings.

    Args:
    sync_client (Union[SyncClient, MemoryCache], optional): The synchronous client to use.
        Defaults to MemoryCache().
    async_client (Union[AsyncClient, AsyncWrapper], optional): The asynchronous client to use.
        Defaults to AsyncWrapper(cache=MemoryCache()).
    default_lock_expiration (Optional[int], optional): The default expiration time for locks.
        Defaults to 30.
    default_cache_ttl (Optional[int], optional): The default cache TTL (time-to-live) for cached values.
        Defaults to None, meaning infinite cache time when ttl is UNSET.
    prefix (str, optional): The prefix to use for keys.
        Defaults to 'PYC-'.
    is_global (bool, optional): Whether to register this client as the global instance.
        Defaults to True.
    """
    if sync_client is None:
        sync_client = MemoryCache()

    if async_client is None:
        async_client = AsyncWrapper(cache=isinstance(sync_client, MemoryCache) and sync_client or MemoryCache())

    global _cachify
    if is_global:
        _cachify = CachifyClient(
            sync_client=sync_client,
            async_client=async_client,
            default_expiration=default_lock_expiration,
            default_cache_ttl=default_cache_ttl,
            prefix=prefix,
        )
        # is not needed, but kept to not ruin the function signature
        return Cachify(
            sync_client=sync_client,
            async_client=async_client,
            prefix=prefix,
            default_expiration=default_lock_expiration,
            default_cache_ttl=default_cache_ttl,
        )

    return Cachify(
        sync_client=sync_client,
        async_client=async_client,
        prefix=prefix,
        default_expiration=default_lock_expiration,
        default_cache_ttl=default_cache_ttl,
    )


def get_cachify_client() -> CachifyClient:
    if _cachify is None:
        raise CachifyInitError('Cachify is not initialized, did you forget to call `init_cachify`?')

    return _cachify
