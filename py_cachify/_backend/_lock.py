import inspect
import logging
import time
from asyncio import sleep as asleep
from functools import partial, wraps
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, TypeVar, Union, cast

from typing_extensions import ParamSpec, Self, deprecated, overload, override

from ._exceptions import CachifyLockError
from ._helpers import a_reset, get_full_key_from_signature, is_alocked, is_coroutine, is_locked, reset
from ._lib import get_cachify
from ._types._common import UNSET, LockProtocolBase, UnsetType
from ._types._lock_wrap import AsyncLockWrappedF, SyncLockWrappedF, WrappedFunctionLock


if TYPE_CHECKING:
    from ._lib import Cachify


logger = logging.getLogger(__name__)
_R = TypeVar('_R', covariant=True)
_P = ParamSpec('_P')
_S = TypeVar('_S')


class AsyncLockMethods(LockProtocolBase):
    async def is_alocked(self) -> bool:
        return bool(await self._cachify.a_get(key=self._key))

    async def _a_acquire(self, key: str) -> None:
        stop_at = self._calc_stop_at()
        c = 10

        while True:
            _is_locked = bool(await self.is_alocked())
            self._raise_if_cached(
                is_already_cached=_is_locked,
                key=key,
                do_raise=self._nowait or time.time() > stop_at,
                do_log=bool(c >= 10),
            )

            if not _is_locked:
                await self._cachify.a_set(key=key, val=1, ttl=self._get_ttl())
                return

            await asleep(0.1)

    async def arelease(self) -> None:
        await self._cachify.a_delete(key=self._key)

    async def __aenter__(self) -> 'Self':
        await self._a_acquire(key=self._key)
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.arelease()


class SyncLockMethods(LockProtocolBase):
    def is_locked(self) -> bool:
        return bool(self._cachify.get(key=self._key))

    def _acquire(self, key: str) -> None:
        stop_at = self._calc_stop_at()
        c = 10

        while True:
            _is_locked = bool(self.is_locked())
            self._raise_if_cached(
                is_already_cached=_is_locked,
                key=key,
                do_raise=self._nowait or time.time() > stop_at,
                do_log=bool(c >= 10),
            )

            if not _is_locked:
                self._cachify.set(key=key, val=1, ttl=self._get_ttl())
                return

            time.sleep(0.1)
            c += 1 if c < 10 else -10

    def release(self) -> None:
        self._cachify.delete(key=self._key)

    def __enter__(self) -> 'Self':
        self._acquire(key=self._key)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


class lock(AsyncLockMethods, SyncLockMethods):
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

    def __init__(
        self,
        key: str,
        nowait: bool = True,
        timeout: Optional[Union[int, float]] = None,
        exp: Union[Optional[int], UnsetType] = UNSET,
    ) -> None:
        self._key = key
        self._nowait = nowait
        self._timeout = timeout
        self._exp = exp

    @overload
    def __call__(self, _func: Callable[_P, Awaitable[_R]]) -> AsyncLockWrappedF[_P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[_P, _R]) -> SyncLockWrappedF[_P, _R]: ...

    def __call__(
        self,
        _func: Union[
            Callable[_P, Awaitable[_R]],
            Callable[_P, _R],
        ],
    ) -> Union[
        AsyncLockWrappedF[_P, _R],
        SyncLockWrappedF[_P, _R],
    ]:
        signature = inspect.signature(_func)

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                bound_args = signature.bind(*args, **kwargs)
                _key = get_full_key_from_signature(bound_args=bound_args, key=self._key)

                async with lock(
                    key=_key,
                    nowait=self._nowait,
                    timeout=self._timeout,
                    exp=self._exp,
                ):
                    return await _awaitable_func(*args, **kwargs)

            setattr(_async_wrapper, 'is_locked', partial(is_alocked, signature=signature, key=self._key))
            setattr(_async_wrapper, 'release', partial(a_reset, signature=signature, key=self._key))

            return cast(AsyncLockWrappedF[_P, _R], cast(object, _async_wrapper))
        else:
            _sync_func = cast(Callable[_P, _R], _func)

            @wraps(_sync_func)
            def _sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                bound_args = signature.bind(*args, **kwargs)
                _key = get_full_key_from_signature(bound_args=bound_args, key=self._key)

                with lock(key=_key, nowait=self._nowait, timeout=self._timeout, exp=self._exp):
                    return _sync_func(*args, **kwargs)

            setattr(_sync_wrapper, 'is_locked', partial(is_locked, signature=signature, key=self._key))
            setattr(_sync_wrapper, 'release', partial(reset, signature=signature, key=self._key))

            return cast(SyncLockWrappedF[_P, _R], cast(object, _sync_wrapper))

    @property
    @override
    def _cachify(self) -> 'Cachify':
        return get_cachify()

    def _recreate_cm(self) -> 'Self':
        return self

    @override
    def _calc_stop_at(self) -> float:
        return time.time() + self._timeout if self._timeout is not None else float('inf')

    @override
    def _get_ttl(self) -> Optional[int]:
        return self._cachify.default_expiration if isinstance(self._exp, UnsetType) else self._exp

    @staticmethod
    @override
    def _raise_if_cached(is_already_cached: bool, key: str, do_raise: bool = True, do_log: bool = True) -> None:
        if not is_already_cached:
            return

        msg = f'{key} is already locked!'

        if do_log:
            logger.warning(msg)

        if do_raise:
            raise CachifyLockError(msg)


def once(key: str, raise_on_locked: bool = False, return_on_locked: Any = None) -> WrappedFunctionLock:
    """
    Decorator that ensures a function is only called once at a time,
        based on a specified key (could be a format string).

    Args:
    key (str): The key used to identify the lock.
    raise_on_locked (bool, optional): If True, raise an exception when the function is already locked.
        Defaults to False.
    return_on_locked (Any, optional): The value to return when the function is already locked.
        Defaults to None.

    Returns:
    SyncOrAsyncRelease: Either a synchronous or asynchronous wrapped function with `release` and `is_locked`
        methods attached to it.
    """

    @overload
    def _once_inner(  # type: ignore[overload-overlap]
        _func: Callable[_P, Awaitable[_R]],
    ) -> AsyncLockWrappedF[_P, _R]: ...

    @overload
    def _once_inner(
        _func: Callable[_P, _R],
    ) -> SyncLockWrappedF[_P, _R]: ...

    def _once_inner(
        _func: Union[Callable[_P, _R], Callable[_P, Awaitable[_R]]],
    ) -> Union[AsyncLockWrappedF[_P, _R], SyncLockWrappedF[_P, _R]]:
        signature = inspect.signature(_func)

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                bound_args = signature.bind(*args, **kwargs)
                _key = get_full_key_from_signature(bound_args=bound_args, key=key)

                try:
                    async with lock(key=_key):
                        return await _awaitable_func(*args, **kwargs)
                except CachifyLockError:
                    if raise_on_locked:
                        raise

                    return return_on_locked  # type: ignore[no-any-return]

            setattr(_async_wrapper, 'release', partial(a_reset, signature=signature, key=key))
            setattr(_async_wrapper, 'is_locked', partial(is_alocked, signature=signature, key=key))

            return cast(AsyncLockWrappedF[_P, _R], cast(object, _async_wrapper))

        else:
            _sync_func = cast(Callable[_P, _R], _func)

            @wraps(_sync_func)
            def _sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                bound_args = signature.bind(*args, **kwargs)
                _key = get_full_key_from_signature(bound_args=bound_args, key=key)

                try:
                    with lock(key=_key):
                        return _sync_func(*args, **kwargs)
                except CachifyLockError:
                    if raise_on_locked:
                        raise

                    return return_on_locked

            setattr(_sync_wrapper, 'release', partial(reset, signature=signature, key=key))
            setattr(_sync_wrapper, 'is_locked', partial(is_locked, signature=signature, key=key))

            return cast(SyncLockWrappedF[_P, _R], cast(object, _sync_wrapper))

    return cast(WrappedFunctionLock, cast(object, _once_inner))


@deprecated('sync_once is deprecated, use once instead. Scheduled for removal in 3.0.0')
def sync_once(key: str, raise_on_locked: bool = False, return_on_locked: Any = None) -> WrappedFunctionLock:
    return once(key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked)


@deprecated('async_once is deprecated, use once instead. Scheduled for removal in 3.0.0')
def async_once(key: str, raise_on_locked: bool = False, return_on_locked: Any = None) -> WrappedFunctionLock:
    return once(key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked)
