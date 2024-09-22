from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Protocol, TypeVar, Union

from typing_extensions import ParamSpec, TypeAlias, overload


if TYPE_CHECKING:
    from .lib import Cachify


R = TypeVar('R', covariant=True)
P = ParamSpec('P')

Encoder: TypeAlias = Callable[[Any], Any]
Decoder: TypeAlias = Callable[[Any], Any]


class AsyncClient(Protocol):
    def get(self, name: str) -> Awaitable[Optional[Any]]:
        raise NotImplementedError

    def delete(self, *names: str) -> Awaitable[Any]:
        raise NotImplementedError

    def set(self, name: str, value: Any, ex: Union[int, None] = None) -> Awaitable[Any]:
        raise NotImplementedError


class SyncClient(Protocol):
    def get(self, name: str) -> Optional[Any]:
        raise NotImplementedError

    def delete(self, *names: str) -> Any:
        raise NotImplementedError

    def set(self, name: str, value: Any, ex: Union[int, None] = None) -> Any:
        raise NotImplementedError


class SyncLockedProto(Protocol[P, R]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...  # pragma: no cover

    def is_locked(self, *args: P.args, **kwargs: P.kwargs) -> bool: ...  # pragma: no cover


class AsyncLockedProto(Protocol[P, R]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...  # pragma: no cover

    def is_locked(self, *args: P.args, **kwargs: P.kwargs) -> bool: ...  # pragma: no cover


class AsyncWithResetProto(Protocol[P, R]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...  # pragma: no cover

    async def reset(self, *args: P.args, **kwargs: P.kwargs) -> None: ...  # pragma: no cover


class SyncWithResetProto(Protocol[P, R]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...  # pragma: no cover

    def reset(self, *args: P.args, **kwargs: P.kwargs) -> None: ...  # pragma: no cover


class SyncOrAsyncReset(Protocol):
    @overload
    def __call__(self, _func: Callable[P, Awaitable[R]]) -> AsyncWithResetProto[P, R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[P, R]) -> SyncWithResetProto[P, R]: ...

    def __call__(
        self, _func: Union[Callable[P, Awaitable[R]], Callable[P, R]]
    ) -> Union[AsyncWithResetProto[P, R], SyncWithResetProto[P, R]]: ...


class UnsetType:
    def __bool__(self) -> bool:
        return False


UNSET = UnsetType()


class LockProtocolBase(Protocol):
    _key: str
    _nowait: bool
    _timeout: Optional[Union[int, float]]
    _exp: Union[Optional[int], UnsetType]

    @staticmethod
    def _raise_if_cached(is_already_cached: bool, key: str, do_raise: bool = True) -> None: ...  # pragma: no cover

    @property
    def _cachify(self) -> 'Cachify': ...  # pragma: no cover

    def _calc_stop_at(self) -> float: ...  # pragma: no cover

    def _get_ttl(self) -> Optional[int]: ...  # pragma: no cover
