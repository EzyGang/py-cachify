from __future__ import annotations

import inspect
import logging
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Generator, Union

from .backend.lib import get_cachify
from .base import AsyncFunc, DecoratorFunc, P, SyncFunc, get_full_key_from_signature
from .exceptions import CachifyLockError


logger = logging.getLogger(__name__)


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


def once(key: str, raise_on_locked: bool = False, return_on_locked: Any = None) -> DecoratorFunc:
    def decorator(_func: Union[SyncFunc, AsyncFunc]) -> Union[SyncFunc, AsyncFunc]:
        @wraps(_func)
        async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            bound_args = inspect.signature(_func).bind(*args, **kwargs)
            try:
                _key = get_full_key_from_signature(bound_args=bound_args, key=key)
                async with async_lock(key=_key):
                    return await _func(*args, **kwargs)
            except CachifyLockError:
                if raise_on_locked:
                    raise

                return return_on_locked

        @wraps(_func)
        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            bound_args = inspect.signature(_func).bind(*args, **kwargs)
            try:
                _key = get_full_key_from_signature(bound_args=bound_args, key=key)
                with lock(key=_key):
                    return _func(*args, **kwargs)
            except CachifyLockError:
                if raise_on_locked:
                    raise

                return return_on_locked

        return _async_wrapper if inspect.iscoroutinefunction(_func) else _sync_wrapper

    return decorator
