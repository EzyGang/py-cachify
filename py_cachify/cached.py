from __future__ import annotations

import inspect
from functools import wraps
from typing import Awaitable, Callable, ParamSpec, TypeVar, Union, cast

from .backend.lib import get_cachify
from .base import get_full_key_from_signature, is_coroutine


R = TypeVar('R')
P = ParamSpec('P')


def cached(
    key: str, ttl: Union[int, None] = None
) -> Callable[[Union[Callable[P, Awaitable[R]], Callable[P, R]]], Union[Callable[P, Awaitable[R]], Callable[P, R]]]:
    def decorator(
        _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
    ) -> Union[Callable[P, R], Callable[P, Awaitable[R]]]:
        signature = inspect.signature(_func)

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                cachify = get_cachify()
                _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
                if val := await cachify.a_get(key=_key):
                    return val

                res = await _awaitable_func(*args, **kwargs)
                await cachify.a_set(key=_key, val=res, ttl=ttl)
                return res

            return cast(Callable[P, Awaitable[R]], _async_wrapper)
        else:

            @wraps(_func)
            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                cachify = get_cachify()
                _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
                if val := cachify.get(key=_key):
                    return val

                res = _func(*args, **kwargs)
                cachify.set(key=_key, val=res, ttl=ttl)
                return cast(R, res)

            return cast(Callable[P, R], _sync_wrapper)

    return decorator
