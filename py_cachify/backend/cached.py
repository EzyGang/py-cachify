import inspect
from functools import partial, wraps
from typing import Awaitable, Callable, Tuple, TypeVar, Union, cast, overload

from typing_extensions import ParamSpec, deprecated

from .helpers import a_reset, encode_decode_value, get_full_key_from_signature, is_coroutine, reset
from .lib import get_cachify
from .types import AsyncWithResetProtocol, Decoder, Encoder, SyncOrAsync, SyncWithResetProtocol


R = TypeVar('R')
P = ParamSpec('P')


def cached(key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None) -> SyncOrAsync:
    @overload
    def _cached_inner(  # type: ignore[overload-overlap]
        _func: Callable[P, Awaitable[R]],
    ) -> AsyncWithResetProtocol[P, R]: ...

    @overload
    def _cached_inner(
        _func: Callable[P, R],
    ) -> SyncWithResetProtocol[P, R]: ...

    def _cached_inner(
        _func: Union[Callable[P, R], Callable[P, Awaitable[R]]],
    ) -> Union[AsyncWithResetProtocol[P, R], SyncWithResetProtocol[P, R]]:
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

            setattr(_async_wrapper, 'reset', partial(a_reset, signature=signature, key=key))

            return cast(AsyncWithResetProtocol[P, R], _async_wrapper)
        else:

            @wraps(_func)  # type: ignore[unreachable]
            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                cachify = get_cachify()
                _key = get_full_key_from_signature(bound_args=signature.bind(*args, **kwargs), key=key)
                if val := cachify.get(key=_key):
                    return encode_decode_value(encoder_decoder=dec, val=val)

                res = _func(*args, **kwargs)
                cachify.set(key=_key, val=encode_decode_value(encoder_decoder=enc, val=res), ttl=ttl)
                return cast(R, res)

            setattr(_sync_wrapper, 'reset', partial(reset, signature=signature, key=key))

            return cast(SyncWithResetProtocol[P, R], _sync_wrapper)

    return _cached_inner


@deprecated('sync_cached is deprecated, use cached instead. Scheduled for removal in 1.3.0')
def sync_cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> SyncOrAsync:
    return cached(key=key, ttl=ttl, enc_dec=enc_dec)


@deprecated('async_cached is deprecated, use cached instead. Scheduled for removal in 1.3.0')
def async_cached(
    key: str, ttl: Union[int, None] = None, enc_dec: Union[Tuple[Encoder, Decoder], None] = None
) -> SyncOrAsync:
    return cached(key=key, ttl=ttl, enc_dec=enc_dec)
