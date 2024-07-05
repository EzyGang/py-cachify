from __future__ import annotations

import inspect
from functools import partial, wraps
from typing import Awaitable, Callable, Optional, Tuple, TypeVar, Union, cast

from typing_extensions import ParamSpec

from py_cachify.backend.lib import get_cachify

from .helpers import Decoder, Encoder, encode_decode_value, get_full_key_from_signature, is_coroutine


R = TypeVar('R')
P = ParamSpec('P')


def _decorator(
    _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
    key: str,
    ttl: Union[int, None] = None,
    enc_dec: Optional[Tuple[Encoder, Decoder]] = None,
) -> Union[Callable[P, R], Callable[P, Awaitable[R]]]:
    signature = inspect.signature(_func)

    enc, dec = None, None
    if enc_dec is not None:
        enc, dec = enc_dec

    if is_coroutine(_func):
        _awaitable_func = _func

        @wraps(_awaitable_func)
        async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cachify = get_cachify()
            _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
            if val := await cachify.a_get(key=_key):
                return encode_decode_value(encoder_decoder=dec, val=val)

            res = await _awaitable_func(*args, **kwargs)
            await cachify.a_set(key=_key, val=encode_decode_value(encoder_decoder=enc, val=res), ttl=ttl)
            return res

        return cast(Callable[P, Awaitable[R]], _async_wrapper)
    else:

        @wraps(_func)
        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            cachify = get_cachify()
            _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
            if val := cachify.get(key=_key):
                return encode_decode_value(encoder_decoder=dec, val=val)

            res = _func(*args, **kwargs)
            cachify.set(key=_key, val=encode_decode_value(encoder_decoder=enc, val=res), ttl=ttl)
            return cast(R, res)

        return cast(Callable[P, R], _sync_wrapper)


def cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> Callable[[Union[Callable[P, Awaitable[R]], Callable[P, R]]], Union[Callable[P, Awaitable[R]], Callable[P, R]]]:
    return cast(
        Callable[[Union[Callable[P, Awaitable[R]], Callable[P, R]]], Union[Callable[P, Awaitable[R]], Callable[P, R]]],
        partial(_decorator, key=key, ttl=ttl, enc_dec=enc_dec),
    )


def sync_cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    return cast(Callable[[Callable[P, R]], Callable[P, R]], partial(_decorator, key=key, ttl=ttl, enc_dec=enc_dec))


def async_cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    return cast(
        Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]],
        partial(_decorator, key=key, ttl=ttl, enc_dec=enc_dec),
    )
