from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias


if TYPE_CHECKING:
    from .._lib import CachifyClient


Encoder: TypeAlias = Callable[[Any], Any]
Decoder: TypeAlias = Callable[[Any], Any]


class AsyncClient(Protocol):
    def get(self, name: str) -> Awaitable[Any | None]:
        raise NotImplementedError

    def delete(self, *names: str) -> Awaitable[Any]:
        raise NotImplementedError

    def set(
        self,
        name: str,
        value: Any,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> Awaitable[Any]:
        raise NotImplementedError


class SyncClient(Protocol):
    def get(self, name: str) -> Any | None:
        raise NotImplementedError

    def delete(self, *names: str) -> Any:
        raise NotImplementedError

    def set(
        self,
        name: str,
        value: Any,
        *,
        ex: int | None = None,
        nx: bool = False,
    ) -> Any:
        raise NotImplementedError


class UnsetType:
    def __bool__(self) -> bool:
        return False


UNSET = UnsetType()


class LockProtocolBase(Protocol):
    _key: str
    _nowait: bool
    _timeout: int | float | None
    _exp: int | None | UnsetType

    @staticmethod
    def _raise_if_cached(
        is_already_cached: bool, key: str, do_raise: bool = True, do_log: bool = True
    ) -> None: ...  # pragma: no cover

    @property
    def _cachify(self) -> 'CachifyClient': ...  # pragma: no cover

    def _calc_stop_at(self) -> float: ...  # pragma: no cover

    def _get_ttl(self) -> int | None: ...  # pragma: no cover
