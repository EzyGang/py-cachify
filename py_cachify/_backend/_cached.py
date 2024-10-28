import inspect
from functools import partial, wraps
from typing import Awaitable, Callable, Tuple, TypeVar, Union, cast, overload

from typing_extensions import ParamSpec, deprecated

from ._helpers import a_reset, encode_decode_value, get_full_key_from_signature, is_coroutine, reset
from ._lib import get_cachify
from ._types._common import Decoder, Encoder
from ._types._reset_wrap import AsyncResetWrappedF, SyncResetWrappedF, WrappedFunctionReset


_R = TypeVar('_R')
_P = ParamSpec('_P')
_S = TypeVar('_S')


def cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> WrappedFunctionReset:
    """
    Decorator that caches the result of a function based on the specified key, time-to-live (ttl),
        and encoding/decoding functions.

    Args:
    key (str): The key used to identify the cached result, could be a format string.
    ttl (Union[int, None], optional): The time-to-live for the cached result.
        Defaults to None, means indefinitely.
    enc_dec (Union[Tuple[Encoder, Decoder], None], optional): The encoding and decoding functions for the cached value.
        Defaults to None.

    Returns:
    WrappedFunctionReset: Either a synchronous or asynchronous function with reset method attached to it,
    reset(*args, **kwargs) matches the type of original function, accepts the same argument,
        and could be used to reset the cache.
    """

    @overload
    def _cached_inner(  # type: ignore[overload-overlap]
        _func: Callable[_P, Awaitable[_R]],
    ) -> AsyncResetWrappedF[_P, _R]: ...

    @overload
    def _cached_inner(
        _func: Callable[_P, _R],
    ) -> SyncResetWrappedF[_P, _R]: ...

    def _cached_inner(
        _func: Union[Callable[_P, Awaitable[_R]], Callable[_P, _R]],
    ) -> Union[AsyncResetWrappedF[_P, _R], SyncResetWrappedF[_P, _R]]:
        signature = inspect.signature(_func)

        enc, dec = None, None
        if enc_dec is not None:
            enc, dec = enc_dec

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                cachify = get_cachify()
                _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
                if val := await cachify.a_get(key=_key):
                    return cast(_R, encode_decode_value(encoder_decoder=dec, val=val))

                res = await _awaitable_func(*args, **kwargs)
                await cachify.a_set(key=_key, val=encode_decode_value(encoder_decoder=enc, val=res), ttl=ttl)
                return res

            setattr(_async_wrapper, 'reset', partial(a_reset, signature=signature, key=key))

            return cast(AsyncResetWrappedF[_P, _R], cast(object, _async_wrapper))
        else:
            _sync_func = cast(Callable[_P, _R], _func)

            @wraps(_sync_func)
            def _sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                cachify = get_cachify()
                _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
                if val := cachify.get(key=_key):
                    return encode_decode_value(encoder_decoder=dec, val=val)

                res = _sync_func(*args, **kwargs)
                cachify.set(key=_key, val=encode_decode_value(encoder_decoder=enc, val=res), ttl=ttl)
                return res

            setattr(_sync_wrapper, 'reset', partial(reset, signature=signature, key=key))

            return cast(SyncResetWrappedF[_P, _R], cast(object, _sync_wrapper))

    return cast(WrappedFunctionReset, cast(object, _cached_inner))


@deprecated('sync_cached is deprecated, use cached instead. Scheduled for removal in 3.0.0')
def sync_cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> WrappedFunctionReset:
    return cached(key=key, ttl=ttl, enc_dec=enc_dec)


@deprecated('async_cached is deprecated, use cached instead. Scheduled for removal in 3.0.0')
def async_cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> WrappedFunctionReset:
    return cached(key=key, ttl=ttl, enc_dec=enc_dec)
