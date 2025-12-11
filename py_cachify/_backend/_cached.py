import inspect
from collections.abc import Awaitable
from functools import partial, wraps
from typing import Callable, Optional, TypeVar, Union, cast, overload

from typing_extensions import ParamSpec

from ._helpers import a_reset, encode_decode_value, get_full_key_from_signature, is_coroutine, reset
from ._lib import CachifyClient, get_cachify_client
from ._types._common import UNSET, Decoder, Encoder, UnsetType
from ._types._reset_wrap import AsyncResetWrappedF, SyncResetWrappedF, WrappedFunctionReset


_R = TypeVar('_R')
_P = ParamSpec('_P')
_S = TypeVar('_S')


def cached(
    key: str,
    ttl: Union[Optional[int], UnsetType] = UNSET,
    enc_dec: Union[tuple[Encoder, Decoder], None] = None,
) -> WrappedFunctionReset:
    """
    Decorator that caches the result of a function based on the specified key, time-to-live (ttl),
        and encoding/decoding functions.

    Args:
    key (str): The key used to identify the cached result, could be a format string.
    ttl (Union[int, None, UnsetType], optional): The time-to-live for the cached result.
        If UNSET (default), the current cachify client's default_cache_ttl is used.
        If None, means indefinitely.
    enc_dec (Union[Tuple[Encoder, Decoder], None], optional): The encoding and decoding functions for the cached value.
        Defaults to None.

    Returns:
    WrappedFunctionReset: Either a synchronous or asynchronous function with reset method attached to it,
    reset(*args, **kwargs) matches the type of original function, accepts the same argument,
        and could be used to reset the cache.
    """

    return _cached_impl(key=key, ttl=ttl, enc_dec=enc_dec, client_provider=get_cachify_client)


def _cached_impl(
    key: str,
    ttl: Union[Optional[int], UnsetType] = UNSET,
    enc_dec: Union[tuple[Encoder, Decoder], None] = None,
    client_provider: Callable[[], CachifyClient] = get_cachify_client,
) -> WrappedFunctionReset:
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

        def _resolve_ttl(client: CachifyClient) -> Optional[int]:
            if isinstance(ttl, UnsetType):
                return client.default_cache_ttl
            return ttl

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                cachify_client = client_provider()
                _key = get_full_key_from_signature(
                    bound_args=signature.bind(*args, **kwargs), key=key, operation_postfix='cached'
                )
                if (val := await cachify_client.a_get(key=_key)) is not None:
                    return cast(_R, encode_decode_value(encoder_decoder=dec, val=val))

                res = await _awaitable_func(*args, **kwargs)

                await cachify_client.a_set(
                    key=_key,
                    val=encode_decode_value(encoder_decoder=enc, val=res),
                    ttl=_resolve_ttl(cachify_client),
                )
                return res

            setattr(
                _async_wrapper,
                'reset',
                partial(
                    a_reset,
                    _pyc_signature=signature,
                    _pyc_key=key,
                    _pyc_operation_postfix='cached',
                    _pyc_original_func=_awaitable_func,
                    _pyc_client_provider=client_provider,
                ),
            )

            return cast(AsyncResetWrappedF[_P, _R], cast(object, _async_wrapper))
        else:
            _sync_func = cast(Callable[_P, _R], _func)  # type: ignore[redundant-cast]

            @wraps(_sync_func)
            def _sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                cachify_client = client_provider()
                _key = get_full_key_from_signature(
                    bound_args=signature.bind(*args, **kwargs), key=key, operation_postfix='cached'
                )
                if (val := cachify_client.get(key=_key)) is not None:
                    return cast(_R, encode_decode_value(encoder_decoder=dec, val=val))

                res = _sync_func(*args, **kwargs)

                cachify_client.set(
                    key=_key,
                    val=encode_decode_value(encoder_decoder=enc, val=res),
                    ttl=_resolve_ttl(cachify_client),
                )
                return res

            setattr(
                _sync_wrapper,
                'reset',
                partial(
                    reset,
                    _pyc_signature=signature,
                    _pyc_key=key,
                    _pyc_operation_postfix='cached',
                    _pyc_original_func=_sync_func,
                    _pyc_client_provider=client_provider,
                ),
            )

            return cast(SyncResetWrappedF[_P, _R], cast(object, _sync_wrapper))

    return cast(WrappedFunctionReset, cast(object, _cached_inner))
