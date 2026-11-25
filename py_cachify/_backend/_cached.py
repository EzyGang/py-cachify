import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from functools import partial, wraps
from typing import Any, TypeVar, cast, overload
from uuid import uuid4

from typing_extensions import ParamSpec

from ._helpers import a_reset, encode_decode_value, get_full_key_from_signature, is_coroutine, reset
from ._lib import CachifyClient, get_cachify_client
from ._logger import logger
from ._single_flight import SingleFlight
from ._types._common import UNSET, Decoder, Encoder, UnsetType
from ._types._reset_wrap import AsyncResetWrappedF, SyncResetWrappedF, WrappedFunctionReset


_R = TypeVar('_R')
_P = ParamSpec('_P')
_S = TypeVar('_S')

# Appended to the full cache key (which always ends in '-cached'). Every other key py-cachify builds ends in
# '-<operation>', so a key ending in '-cached_lock' can't be produced by `cached`, `lock`, `once` or `pool`.
_FILL_LOCK_SUFFIX = '_lock'


def cached(
    key: str,
    ttl: int | None | UnsetType = UNSET,
    enc_dec: tuple[Encoder, Decoder] | None = None,
    *,
    single_flight: bool = True,
    lock: bool = False,
    lock_exp: int | None | UnsetType = UNSET,
    lock_wait: float | None | UnsetType = UNSET,
    lock_poll_interval: float | UnsetType = UNSET,
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
    single_flight (bool, optional): Concurrent misses for the same key in this process share one call
        of the function. Defaults to True.
    lock (bool, optional): On a miss, take a lock in the cache backend so that one process computes
        the value while the others wait for it. Defaults to False.
    lock_exp (Union[int, None, UnsetType], optional): Expiration of that lock in seconds.
        Defaults to the current cachify client's default_lock_expiration.
    lock_wait (Union[float, None, UnsetType], optional): How long a caller waits for another process's value
        before computing it without the lock. Defaults to lock_exp; None waits as long as the lock exists.
    lock_poll_interval (Union[float, UnsetType], optional): Seconds between checks while waiting.
        Defaults to the current cachify client's lock_poll_interval.

    Returns:
    WrappedFunctionReset: Either a synchronous or asynchronous function with reset method attached to it,
    reset(*args, **kwargs) matches the type of original function, accepts the same argument,
        and could be used to reset the cache.
    """

    return _cached_impl(
        key=key,
        ttl=ttl,
        enc_dec=enc_dec,
        single_flight=single_flight,
        lock=lock,
        lock_exp=lock_exp,
        lock_wait=lock_wait,
        lock_poll_interval=lock_poll_interval,
        client_provider=get_cachify_client,
    )


def _cached_impl(
    key: str,
    ttl: int | None | UnsetType = UNSET,
    enc_dec: tuple[Encoder, Decoder] | None = None,
    single_flight: bool = True,
    lock: bool = False,
    lock_exp: int | None | UnsetType = UNSET,
    lock_wait: float | None | UnsetType = UNSET,
    lock_poll_interval: float | UnsetType = UNSET,
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
        _func: Callable[_P, Awaitable[_R]] | Callable[_P, _R],
    ) -> AsyncResetWrappedF[_P, _R] | SyncResetWrappedF[_P, _R]:
        signature = inspect.signature(_func)
        flight = SingleFlight() if single_flight else None

        enc, dec = None, None
        if enc_dec is not None:
            enc, dec = enc_dec

        def _resolve_ttl(client: CachifyClient) -> int | None:
            if isinstance(ttl, UnsetType):
                return client.default_cache_ttl
            return ttl

        def _decoded(val: Any) -> _R:
            return cast(_R, encode_decode_value(encoder_decoder=dec, val=val))

        def _lock_settings(client: CachifyClient) -> tuple[int | None, float, float]:
            """Returns the lock expiration, the time to stop waiting at and the poll interval."""
            exp = client.default_expiration if isinstance(lock_exp, UnsetType) else lock_exp
            wait = exp if isinstance(lock_wait, UnsetType) else lock_wait
            poll = client.lock_poll_interval if isinstance(lock_poll_interval, UnsetType) else lock_poll_interval
            return exp, time.monotonic() + wait if wait is not None else float('inf'), poll

        if is_coroutine(_func):
            _awaitable_func = _func

            async def _astore(client: CachifyClient, _key: str, call: Callable[[], Awaitable[_R]]) -> _R:
                res = await call()
                await client.a_set(
                    key=_key,
                    val=encode_decode_value(encoder_decoder=enc, val=res),
                    ttl=_resolve_ttl(client),
                )
                return res

            async def _alocked(client: CachifyClient, _key: str, call: Callable[[], Awaitable[_R]]) -> _R:
                exp, stop_at, poll = _lock_settings(client)
                lock_key, token = f'{_key}{_FILL_LOCK_SUFFIX}', uuid4().hex

                while not await client.a_try_acquire_lock(key=lock_key, ttl=exp, token=token):
                    if (remaining := stop_at - time.monotonic()) <= 0:
                        logger.debug(f'{lock_key} is still locked, computing {_key} without the lock')
                        return await _astore(client, _key, call)

                    await asyncio.sleep(min(poll, remaining))
                    if (val := await client.a_get(key=_key)) is not None:
                        return _decoded(val)

                try:
                    if (val := await client.a_get(key=_key)) is not None:
                        return _decoded(val)
                    return await _astore(client, _key, call)
                finally:
                    await client.a_release_lock(key=lock_key, token=token)

            async def _afill(client: CachifyClient, _key: str, call: Callable[[], Awaitable[_R]]) -> _R:
                if lock:
                    return await _alocked(client, _key, call)
                return await _astore(client, _key, call)

            async def _alead(client: CachifyClient, _key: str, call: Callable[[], Awaitable[_R]]) -> _R:
                # The cache may have been filled between the caller's miss and the start of this computation.
                if (val := await client.a_get(key=_key)) is not None:
                    return _decoded(val)
                return await _afill(client, _key, call)

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                cachify_client = client_provider()
                _key = get_full_key_from_signature(
                    bound_args=signature.bind(*args, **kwargs), key=key, operation_postfix='cached'
                )
                if (val := await cachify_client.a_get(key=_key)) is not None:
                    return cast(_R, encode_decode_value(encoder_decoder=dec, val=val))

                call = partial(_awaitable_func, *args, **kwargs)
                if flight is None:
                    return await _afill(cachify_client, _key, call)
                return await flight.arun(_key, partial(_alead, cachify_client, _key, call))

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

            def _store(client: CachifyClient, _key: str, call: Callable[[], _R]) -> _R:
                res = call()
                client.set(
                    key=_key,
                    val=encode_decode_value(encoder_decoder=enc, val=res),
                    ttl=_resolve_ttl(client),
                )
                return res

            def _locked(client: CachifyClient, _key: str, call: Callable[[], _R]) -> _R:
                exp, stop_at, poll = _lock_settings(client)
                lock_key, token = f'{_key}{_FILL_LOCK_SUFFIX}', uuid4().hex

                while not client.try_acquire_lock(key=lock_key, ttl=exp, token=token):
                    if (remaining := stop_at - time.monotonic()) <= 0:
                        logger.debug(f'{lock_key} is still locked, computing {_key} without the lock')
                        return _store(client, _key, call)

                    time.sleep(min(poll, remaining))
                    if (val := client.get(key=_key)) is not None:
                        return _decoded(val)

                try:
                    if (val := client.get(key=_key)) is not None:
                        return _decoded(val)
                    return _store(client, _key, call)
                finally:
                    client.release_lock(key=lock_key, token=token)

            def _fill(client: CachifyClient, _key: str, call: Callable[[], _R]) -> _R:
                if lock:
                    return _locked(client, _key, call)
                return _store(client, _key, call)

            def _lead(client: CachifyClient, _key: str, call: Callable[[], _R]) -> _R:
                # The cache may have been filled between the caller's miss and the start of this computation.
                if (val := client.get(key=_key)) is not None:
                    return _decoded(val)
                return _fill(client, _key, call)

            @wraps(_sync_func)
            def _sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                cachify_client = client_provider()
                _key = get_full_key_from_signature(
                    bound_args=signature.bind(*args, **kwargs), key=key, operation_postfix='cached'
                )
                if (val := cachify_client.get(key=_key)) is not None:
                    return cast(_R, encode_decode_value(encoder_decoder=dec, val=val))

                call = partial(_sync_func, *args, **kwargs)
                if flight is None:
                    return _fill(cachify_client, _key, call)
                return flight.run(_key, partial(_lead, cachify_client, _key, call))

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
