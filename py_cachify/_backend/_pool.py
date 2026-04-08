import contextvars
import inspect
import time
import uuid
from collections.abc import Awaitable
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar, Union, cast

from typing_extensions import ParamSpec, Self, final, overload

from ._exceptions import CachifyLockError, CachifyPoolFullError
from ._helpers import get_full_key_from_signature, is_coroutine
from ._lib import get_cachify_client
from ._pool_state import PoolState
from ._types._common import UNSET, UnsetType
from ._types._pool_wrap import AsyncPoolWrappedF, SyncPoolWrappedF, WrappedFunctionPool


if TYPE_CHECKING:
    from ._lib import CachifyClient

_P = ParamSpec('_P')
_R = TypeVar('_R', covariant=True)


class _PoolBase:
    """Shared pool functionality and state management."""

    def __init__(
        self,
        key: str,
        max_size: int,
        slot_exp: Union[Optional[int], UnsetType] = UNSET,
    ) -> None:
        self._key = key
        self._max_size = max_size
        self._slot_exp = slot_exp
        self._bound_cachify_client: Optional[CachifyClient] = None
        self._slot_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
            f'pool-slot-{key}', default=None
        )

    @property
    def _cachify(self) -> 'CachifyClient':
        if self._bound_cachify_client is not None:
            return self._bound_cachify_client
        return get_cachify_client()

    @_cachify.setter
    def _cachify(self, client: 'CachifyClient') -> None:
        self._bound_cachify_client = client

    def _get_slot_expiration(self) -> Optional[int]:
        if isinstance(self._slot_exp, UnsetType):
            return self._cachify.default_pool_slot_expiration
        return self._slot_exp

    def _get_meta_lock_key(self) -> str:
        return f'{self._key}-lock'

    def _get_state_key(self) -> str:
        return f'{self._key}-state'

    def _get_lock_timeout(self) -> float:
        """Calculate meta-lock timeout based on max_size.

        Scales from 5s (small pools) to 30s (large pools).
        Formula: min(30, max(5, max_size * 0.1))
        Examples:
            max_size=5  -> 5s
            max_size=10 -> 5s
            max_size=50 -> 5s
            max_size=100 -> 10s
            max_size=300 -> 30s
        """
        return min(30.0, max(5.0, self._max_size * 0.1))


class _PoolSync(_PoolBase):
    """Synchronous pool operations."""

    def _load_state(self) -> PoolState:
        state_key = self._get_state_key()
        data = self._cachify.get(key=state_key)
        if data and isinstance(data, PoolState):
            return data

        return PoolState()

    def _save_state(self, state: PoolState) -> None:
        state_key = self._get_state_key()
        _ = self._cachify.set(key=state_key, val=state)

    def _acquire_slot(self) -> Optional[str]:
        now = time.time()
        state = self._load_state()
        state.cleanup(now)

        if state.count >= self._max_size:
            return None

        slot_id = uuid.uuid4().hex
        slot_exp = self._get_slot_expiration()
        expiration_time = now + slot_exp if slot_exp is not None else float('inf')
        state.slots[slot_id] = expiration_time
        self._save_state(state)

        return slot_id

    def _release_slot(self, slot_id: str) -> None:
        state = self._load_state()
        if slot_id in state.slots:
            del state.slots[slot_id]
            self._save_state(state)

    def _acquire_or_raise(self) -> str:
        """Try to acquire a slot. Raises CachifyPoolFullError if pool is full."""
        from ._lock import lock as _lock_cls

        meta_lock = _lock_cls(key=self._get_meta_lock_key(), nowait=False, timeout=self._get_lock_timeout())
        meta_lock._cachify = self._cachify  # pyright: ignore[reportPrivateUsage]

        try:
            with meta_lock:
                slot_id = self._acquire_slot()

            if slot_id is None:
                raise CachifyPoolFullError(f'{self._key} is full (max_size={self._max_size})')
            return slot_id
        except CachifyLockError:
            raise CachifyPoolFullError(f'{self._key} is full (max_size={self._max_size})') from None

    def _release_with_lock(self, slot_id: str) -> None:
        """Release a slot with meta-lock protection."""
        from ._lock import lock as _lock_cls

        meta_lock = _lock_cls(key=self._get_meta_lock_key(), nowait=False, timeout=self._get_lock_timeout())
        meta_lock._cachify = self._cachify  # pyright: ignore[reportPrivateUsage]

        with meta_lock:
            self._release_slot(slot_id)

    def _enter(self) -> Self:
        slot_id = self._acquire_or_raise()
        self._slot_id_var.set(slot_id)
        return self

    def __enter__(self) -> Self:
        return self._enter()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        slot_id = self._slot_id_var.get()
        if slot_id:
            self._release_with_lock(slot_id)
        self._slot_id_var.set(None)

    def size(self) -> int:
        from ._lock import lock as _lock_cls

        meta_lock = _lock_cls(key=self._get_meta_lock_key(), nowait=False, timeout=self._get_lock_timeout())
        meta_lock._cachify = self._cachify  # pyright: ignore[reportPrivateUsage]

        with meta_lock:
            state = self._load_state()
            return state.cleanup(time.time())


class _PoolAsync(_PoolBase):
    """Asynchronous pool operations."""

    async def _aload_state(self) -> PoolState:
        state_key = self._get_state_key()
        data = await self._cachify.a_get(key=state_key)
        if data and isinstance(data, PoolState):
            return data

        return PoolState()

    async def _asave_state(self, state: PoolState) -> None:
        state_key = self._get_state_key()
        _ = await self._cachify.a_set(key=state_key, val=state)

    async def _a_acquire_slot(self) -> Optional[str]:
        now = time.time()
        state = await self._aload_state()
        state.cleanup(now)

        if state.count >= self._max_size:
            return None

        slot_id = uuid.uuid4().hex
        slot_exp = self._get_slot_expiration()
        expiration_time = now + slot_exp if slot_exp is not None else float('inf')
        state.slots[slot_id] = expiration_time
        await self._asave_state(state)

        return slot_id

    async def _a_release_slot(self, slot_id: str) -> None:
        state = await self._aload_state()
        if slot_id in state.slots:
            del state.slots[slot_id]
            await self._asave_state(state)

    async def _a_acquire_or_raise(self) -> str:
        """Try to acquire a slot. Raises CachifyPoolFullError if pool is full."""
        from ._lock import lock as _lock_cls

        meta_lock = _lock_cls(key=self._get_meta_lock_key(), nowait=False, timeout=self._get_lock_timeout())
        meta_lock._cachify = self._cachify  # pyright: ignore[reportPrivateUsage]

        try:
            async with meta_lock:
                slot_id = await self._a_acquire_slot()

            if slot_id is None:
                raise CachifyPoolFullError(f'{self._key} is full (max_size={self._max_size})')
            return slot_id
        except CachifyLockError:
            raise CachifyPoolFullError(f'{self._key} is full (max_size={self._max_size})') from None

    async def _a_release_with_lock(self, slot_id: str) -> None:
        """Release a slot with meta-lock protection."""
        from ._lock import lock as _lock_cls

        meta_lock = _lock_cls(key=self._get_meta_lock_key(), nowait=False, timeout=self._get_lock_timeout())
        meta_lock._cachify = self._cachify  # pyright: ignore[reportPrivateUsage]

        async with meta_lock:
            await self._a_release_slot(slot_id)

    async def _aenter(self) -> Self:
        slot_id = await self._a_acquire_or_raise()
        self._slot_id_var.set(slot_id)
        return self

    async def __aenter__(self) -> Self:
        return await self._aenter()

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        slot_id = self._slot_id_var.get()
        if slot_id:
            await self._a_release_with_lock(slot_id)
        self._slot_id_var.set(None)

    async def asize(self) -> int:
        from ._lock import lock as _lock_cls

        meta_lock = _lock_cls(key=self._get_meta_lock_key(), nowait=False, timeout=self._get_lock_timeout())
        meta_lock._cachify = self._cachify  # pyright: ignore[reportPrivateUsage]

        async with meta_lock:
            state = await self._aload_state()
            return state.cleanup(time.time())


@final
class pool(_PoolSync, _PoolAsync):
    """Pool implementation using counter + meta-lock with set-based state.

    Manages a pool of slots with a maximum size. Supports both sync and async operations.

    Args:
        key (str): The key used to identify the pool.
        max_size (int): Maximum number of concurrent slots in the pool.
        raise_on_full (bool): If True, raise CachifyPoolFullError when pool is full. Defaults to False.
        slot_exp (Union[Optional[int], UnsetType]): TTL for pool slots. Uses default_pool_slot_expiration if UNSET.

    Usage as context manager:
        async with pool(key='worker-pool', max_size=10):
            ...

        with pool(key='sync-pool', max_size=5):
            ...

    Usage as decorator via pooled() method:
        main_pool = pool(key='worker-pool', max_size=10)

        @main_pool.pooled(on_full=handler)
        async def process_task() -> None:
            ...
    """

    def pooled(
        self,
        on_full: Optional[Callable[..., Any]] = None,
        raise_on_full: bool = False,
    ) -> WrappedFunctionPool:
        """Use pool instance as decorator factory.

        Args:
            on_full: Optional callback when pool is full. Receives *args, **kwargs from function call.
            raise_on_full: If True, raise CachifyPoolFullError when pool is full instead of calling on_full.

        Example:
            main_pool = pool(key='worker', max_size=10)

            @main_pool.pooled(on_full=handler)
            async def process():
                ...
        """
        return _pooled_impl(
            key=self._key,
            max_size=self._max_size,
            on_full=on_full,
            raise_on_full=raise_on_full,
            slot_exp=self._slot_exp,
            pool_instance=self,
        )


def _pooled_impl(
    key: str,
    max_size: int,
    on_full: Optional[Callable[..., Any]] = None,
    raise_on_full: bool = False,
    slot_exp: Union[Optional[int], UnsetType] = UNSET,
    pool_instance: Optional['pool'] = None,
    client_provider: Callable[[], 'CachifyClient'] = get_cachify_client,
) -> WrappedFunctionPool:
    """Internal pooled decorator implementation with optional pool_instance or client_provider."""

    def _get_pool(bound_args: inspect.BoundArguments) -> 'pool':
        """Get pool instance - use provided or create new one."""
        if pool_instance is not None:
            return pool_instance

        _key = get_full_key_from_signature(bound_args=bound_args, key=key, operation_postfix='pool')
        _pool = pool(key=_key, max_size=max_size, slot_exp=slot_exp)
        _pool._cachify = client_provider()  # pyright: ignore[reportPrivateUsage]

        return _pool

    @overload
    def _pooled_inner(  # type: ignore[overload-overlap]
        _func: Callable[_P, Awaitable[_R]],
    ) -> AsyncPoolWrappedF[_P, Optional[_R]]: ...

    @overload
    def _pooled_inner(
        _func: Callable[_P, _R],
    ) -> SyncPoolWrappedF[_P, Optional[_R]]: ...

    def _pooled_inner(
        _func: Union[Callable[_P, _R], Callable[_P, Awaitable[_R]]],
    ) -> Union[AsyncPoolWrappedF[_P, Optional[_R]], SyncPoolWrappedF[_P, Optional[_R]]]:
        signature = inspect.signature(_func)

        if is_coroutine(_func):
            _awaitable_func = _func

            @wraps(_awaitable_func)
            async def _async_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> Optional[_R]:
                bound_args = signature.bind(*args, **kwargs)
                _pool = _get_pool(bound_args)

                try:
                    async with _pool:
                        return await _awaitable_func(*args, **kwargs)
                except CachifyPoolFullError:
                    if raise_on_full:
                        raise
                    if on_full:
                        result = on_full(*args, **kwargs)
                        if inspect.iscoroutine(result):
                            return await result
                        return result

                    return None

            async def _size(*args: Any, **kwargs: Any) -> int:
                bound_args = signature.bind(*args, **kwargs)
                _pool = _get_pool(bound_args)
                return await _pool.asize()

            setattr(_async_wrapper, 'size', _size)
            return cast(AsyncPoolWrappedF[_P, Optional[_R]], cast(object, _async_wrapper))
        else:
            _sync_func = cast(Callable[_P, _R], _func)

            @wraps(_sync_func)
            def _sync_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> Optional[_R]:
                bound_args = signature.bind(*args, **kwargs)
                _pool = _get_pool(bound_args)

                try:
                    with _pool:
                        return _sync_func(*args, **kwargs)
                except CachifyPoolFullError:
                    if raise_on_full:
                        raise
                    if on_full:
                        return on_full(*args, **kwargs)

                    return None

            def _sync_size(*args: Any, **kwargs: Any) -> int:
                bound_args = signature.bind(*args, **kwargs)
                _pool = _get_pool(bound_args)
                return _pool.size()

            setattr(_sync_wrapper, 'size', _sync_size)
            return cast(SyncPoolWrappedF[_P, Optional[_R]], cast(object, _sync_wrapper))

    return cast(WrappedFunctionPool, cast(object, _pooled_inner))


def pooled(
    key: str,
    max_size: int,
    on_full: Optional[Callable[..., Any]] = None,
    raise_on_full: bool = False,
    slot_exp: Union[Optional[int], UnsetType] = UNSET,
) -> WrappedFunctionPool:
    """Standalone decorator factory for pooled functions.

    Args:
        key: Pool key (supports format strings with function args)
        max_size: Maximum concurrent executions
        on_full: Callback called when pool is full (receives function args)
        raise_on_full: If True, raise CachifyPoolFullError when pool is full instead of calling on_full.
        slot_exp: TTL for pool slots in seconds

    Returns:
        Decorator that wraps functions with pool acquisition

    Example:
        @pooled(key='pool-{user_id}', max_size=10, on_full=handle_full)
        async def process(user_id: str) -> None:
            ...
    """
    return _pooled_impl(
        key=key,
        max_size=max_size,
        on_full=on_full,
        raise_on_full=raise_on_full,
        slot_exp=slot_exp,
        pool_instance=None,
        client_provider=get_cachify_client,
    )
