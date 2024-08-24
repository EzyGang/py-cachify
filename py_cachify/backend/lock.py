import inspect
import logging
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, TypeVar, Union

from typing_extensions import ParamSpec, deprecated, overload

from .exceptions import CachifyLockError
from .helpers import SyncOrAsync, get_full_key_from_signature, is_coroutine
from .lib import get_cachify


logger = logging.getLogger(__name__)
R = TypeVar('R')
P = ParamSpec('P')


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
    def _once_inner(
        _func: Callable[P, Awaitable[R]],
    ) -> Callable[P, Awaitable[R]]: ...

    @overload
    def _once_inner(
        _func: Callable[P, R],
    ) -> Callable[P, R]: ...

    def _once_inner(  # type: ignore[misc]
        _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
    ) -> Union[Callable[P, R], Callable[P, Awaitable[R]]]:
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

            return _async_wrapper

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

            return _sync_wrapper

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
