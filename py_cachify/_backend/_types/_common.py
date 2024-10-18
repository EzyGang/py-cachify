from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Protocol, TypeVar, Union

from typing_extensions import ParamSpec, TypeAlias


if TYPE_CHECKING:
    from .._lib import Cachify


_R = TypeVar('_R')
_P = ParamSpec('_P')
_S = TypeVar('_S')

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
    def _raise_if_cached(
        is_already_cached: bool, key: str, do_raise: bool = True, do_log: bool = True
    ) -> None: ...  # pragma: no cover

    @property
    def _cachify(self) -> 'Cachify': ...  # pragma: no cover

    def _calc_stop_at(self) -> float: ...  # pragma: no cover

    def _get_ttl(self) -> Optional[int]: ...  # pragma: no cover
