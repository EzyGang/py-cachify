import inspect
import logging
from contextlib import asynccontextmanager, contextmanager
from functools import partial, wraps
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Optional,
    Protocol,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import ParamSpec, deprecated, overload

from .exceptions import CachifyLockError
from .helpers import a_reset, get_full_key_from_signature, is_coroutine, reset
from .lib import get_cachify
from .types import AsyncWithResetProtocol, SyncOrAsync, SyncWithResetProtocol


if TYPE_CHECKING:
    from .lib import Cachify


logger = logging.getLogger(__name__)
R = TypeVar('R')
P = ParamSpec('P')


def _check_is_cached(is_already_cached: bool, key: str) -> None:
    if not is_already_cached:
        return

    logger.warning(msg := f'{key} is already locked!')
    raise CachifyLockError(msg)


class LockProtocolBase(Protocol):
    _cachify: 'Cachify'
    _key: str
    _reentrant: bool
    _nowait: bool
    _timeout: Optional[int]

    @staticmethod
    def _check_is_cached(is_already_cached: bool, key: str) -> None: ...


class AsyncLockMethods(LockProtocolBase):
    async def _a_acquire(self, key: str) -> None:
        cached = await self._cachify.a_get(key=key)
        self._check_is_cached(is_already_cached=bool(cached), key=key)

        await self._cachify.a_set(key=key, val=1)

    async def _a_release(self, key: str) -> None:
        await self._cachify.a_delete(key=key)

    async def __aenter__(self, key: Optional[str] = None) -> None:
        await self._a_acquire(key=key or self._key)

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self._a_release(key=self._key)


class SyncLockMethods(LockProtocolBase):
    def _acquire(self, key: str) -> None:
        cached = self._cachify.get(key=key)
        self._check_is_cached(is_already_cached=bool(cached), key=key)

        self._cachify.set(key=key, val=1)

    def _release(self, key: str) -> None:
        self._cachify.delete(key=key)

    def __enter__(self) -> None:
        self._acquire(key=self._key)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._release(key=self._key)


class Lock(AsyncLockMethods, SyncLockMethods):
    def __init__(self, key: str, reentrant: bool = False, nowait: bool = True, timeout: Optional[int] = None) -> None:
        self._key = key
        self._reentrant = reentrant
        self._nowait = nowait
        self._timeout = timeout

    def __call__(
        self, func: Union[Callable[P, R], Callable[P, Awaitable[R]]]
    ) -> Union[SyncWithResetProtocol[P, R], AsyncWithResetProtocol[P, R]]:
        @overload
        def _lock_inner(  # type: ignore[overload-overlap]
            _func: Callable[P, Awaitable[R]],
        ) -> AsyncWithResetProtocol[P, R]: ...

        @overload
        def _lock_inner(
            _func: Callable[P, R],
        ) -> SyncWithResetProtocol[P, R]: ...

        def _lock_inner(
            _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
        ) -> Union[SyncWithResetProtocol[P, R], AsyncWithResetProtocol[P, R]]:
            signature = inspect.signature(_func)

            if is_coroutine(_func):
                _awaitable_func = _func

                @wraps(_awaitable_func)
                async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                    bound_args = signature.bind(*args, **kwargs)
                    _key = get_full_key_from_signature(bound_args=bound_args, key=self._key)

                    # try:
                    #     async with self.__aenter__(key=_key):
                    #         return await _awaitable_func(*args, **kwargs)
                    # except CachifyLockError:
                    #     if raise_on_locked:
                    #         raise
                    #
                    #     return return_on_locked

                setattr(_async_wrapper, 'reset', partial(a_reset, signature=signature, key=key))

                return cast(AsyncWithResetProtocol[P, R], _async_wrapper)

            else:

                @wraps(_func)  # type: ignore[unreachable]
                def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                    bound_args = signature.bind(*args, **kwargs)
                    _key = get_full_key_from_signature(bound_args=bound_args, key=key)

                    # try:
                    #     with lock(key=_key):
                    #         return _func(*args, **kwargs)
                    # except CachifyLockError:
                    #     if raise_on_locked:
                    #         raise
                    #
                    #     return return_on_locked

                setattr(_sync_wrapper, 'reset', partial(reset, signature=signature, key=key))

                return cast(SyncWithResetProtocol[P, R], _sync_wrapper)

        return _lock_inner

    def _recreate_cm(self):
        return self

    @property
    def _cachify(self) -> 'Cachify':
        return get_cachify()

    @staticmethod
    def _check_is_cached(is_already_cached: bool, key: str) -> None:
        if not is_already_cached:
            return

        logger.warning(msg := f'{key} is already locked!')
        raise CachifyLockError(msg)


@asynccontextmanager
async def async_lock(key: str) -> AsyncGenerator[None, None]:
    _cachify = get_cachify()
    cached = await _cachify.a_get(key=key)
    _check_is_cached(is_already_cached=bool(cached), key=key)

    await _cachify.a_set(key=key, val=1)
    try:
        yield
    finally:
        await _cachify.a_delete(key=key)


@contextmanager
def lock(key: str) -> Generator[None, None, None]:
    _cachify = get_cachify()
    cached = _cachify.get(key=key)
    _check_is_cached(is_already_cached=bool(cached), key=key)

    _cachify.set(key=key, val=1)
    try:
        yield
    finally:
        _cachify.delete(key=key)


def once(key: str, raise_on_locked: bool = False, return_on_locked: Any = None) -> SyncOrAsync:
    @overload
    def _once_inner(  # type: ignore[overload-overlap]
        _func: Callable[P, Awaitable[R]],
    ) -> AsyncWithResetProtocol[P, R]: ...

    @overload
    def _once_inner(
        _func: Callable[P, R],
    ) -> SyncWithResetProtocol[P, R]: ...

    def _once_inner(
        _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
    ) -> Union[SyncWithResetProtocol[P, R], AsyncWithResetProtocol[P, R]]:
        signature = inspect.signature(_func)

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                bound_args = signature.bind(*args, **kwargs)
                _key = get_full_key_from_signature(bound_args=bound_args, key=key)

                try:
                    async with async_lock(key=_key):
                        return await _awaitable_func(*args, **kwargs)
                except CachifyLockError:
                    if raise_on_locked:
                        raise

                    return return_on_locked

            setattr(_async_wrapper, 'reset', partial(a_reset, signature=signature, key=key))

            return cast(AsyncWithResetProtocol[P, R], _async_wrapper)

        else:

            @wraps(_func)  # type: ignore[unreachable]
            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
                bound_args = signature.bind(*args, **kwargs)
                _key = get_full_key_from_signature(bound_args=bound_args, key=key)

                try:
                    with lock(key=_key):
                        return _func(*args, **kwargs)
                except CachifyLockError:
                    if raise_on_locked:
                        raise

                    return return_on_locked

            setattr(_sync_wrapper, 'reset', partial(reset, signature=signature, key=key))

            return cast(SyncWithResetProtocol[P, R], _sync_wrapper)

    return _once_inner


@deprecated('sync_once is deprecated, use once instead. Scheduled for removal in 1.3.0')
def sync_once(
    key: str, raise_on_locked: bool = False, return_on_locked: Any = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return once(key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked)


@deprecated('async_once is deprecated, use once instead. Scheduled for removal in 1.3.0')
def async_once(
    key: str, raise_on_locked: bool = False, return_on_locked: Any = None
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return once(key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked)
