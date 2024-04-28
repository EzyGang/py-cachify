from __future__ import annotations

import inspect
import logging
from contextlib import asynccontextmanager, contextmanager
from functools import partial, wraps
from typing import Any, AsyncGenerator, Awaitable, Callable, Generator, TypeVar, Union, cast

from typing_extensions import ParamSpec

from .exceptions import CachifyLockError
from .helpers import get_full_key_from_signature, is_coroutine
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


def _decorator(
    _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
    key: str,
    raise_on_locked: bool = False,
    return_on_locked: Any = None,
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

        return cast(Callable[P, Awaitable[R]], _async_wrapper)

    else:

        @wraps(_func)
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

        return cast(Callable[P, R], _sync_wrapper)


def once(
    key: str, raise_on_locked: bool = False, return_on_locked: Any = None
) -> Callable[[Union[Callable[P, Awaitable[R]], Callable[P, R]]], Union[Callable[P, Awaitable[R]], Callable[P, R]]]:
    return cast(
        Callable[[Union[Callable[P, Awaitable[R]], Callable[P, R]]], Union[Callable[P, Awaitable[R]], Callable[P, R]]],
        partial(_decorator, key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked),
    )


def sync_once(
    key: str, raise_on_locked: bool = False, return_on_locked: Any = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return cast(
        Callable[[Callable[P, R]], Callable[P, R]],
        partial(_decorator, key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked),
    )


def async_once(
    key: str, raise_on_locked: bool = False, return_on_locked: Any = None
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return cast(
        Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]],
        partial(_decorator, key=key, raise_on_locked=raise_on_locked, return_on_locked=return_on_locked),
    )
