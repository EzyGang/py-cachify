from __future__ import annotations

import asyncio
import inspect
from functools import wraps
from typing import Any, Union

from .backend.lib import get_cachify
from .base import AsyncFunc, DecoratorFunc, P, SyncFunc, get_full_key_from_signature


def cached(key: str, ttl: Union[int, None] = None) -> DecoratorFunc:
    def decorator(_func: Union[SyncFunc, AsyncFunc]) -> Union[SyncFunc, AsyncFunc]:
        signature = inspect.signature(_func)

        @wraps(_func)
        async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            cachify = get_cachify()
            _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
            if val := await cachify.a_get(key=_key):
                return val

            res = await _func(*args, **kwargs)
            await cachify.a_set(key=_key, val=res, ttl=ttl)
            return res

        @wraps(_func)
        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            cachify = get_cachify()
            _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
            if val := cachify.get(key=_key):
                return val

            res = _func(*args, **kwargs)
            cachify.set(key=_key, val=res, ttl=ttl)
            return res

        return _async_wrapper if asyncio.iscoroutinefunction(_func) else _sync_wrapper

    return decorator
