from typing import Any, Awaitable, Callable, Optional, Protocol, TypeVar, Union

from typing_extensions import ParamSpec, TypeAlias, overload


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


class AsyncWithResetProtocol(Protocol[P, R]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...  # pragma: no cover

    async def reset(self, *args: P.args, **kwargs: P.kwargs) -> None: ...  # pragma: no cover


class SyncWithResetProtocol(Protocol[P, R]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R: ...  # pragma: no cover

    def reset(self, *args: P.args, **kwargs: P.kwargs) -> None: ...  # pragma: no cover


class SyncOrAsync(Protocol):
    @overload
    def __call__(self, _func: Callable[P, Awaitable[R]]) -> AsyncWithResetProtocol[P, R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[P, R]) -> SyncWithResetProtocol[P, R]: ...

    def __call__(
        self, _func: Union[Callable[P, Awaitable[R]], Callable[P, R]]
    ) -> Union[AsyncWithResetProtocol[P, R], SyncWithResetProtocol[P, R]]: ...
