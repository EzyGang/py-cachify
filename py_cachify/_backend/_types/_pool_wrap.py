from collections.abc import Awaitable
from typing import Callable, Union

from typing_extensions import ParamSpec, Protocol, TypeVar, overload


_R = TypeVar('_R')
_P = ParamSpec('_P')


class AsyncPoolWrappedF(Protocol[_P, _R]):
    """Protocol for async functions wrapped with @pooled decorator."""

    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    async def size(self, *args: _P.args, **kwargs: _P.kwargs) -> int: ...  # pragma: no cover


class SyncPoolWrappedF(Protocol[_P, _R]):
    """Protocol for sync functions wrapped with @pooled decorator."""

    __wrapped__: Callable[_P, _R]  # pragma: no cover

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    def size(self, *args: _P.args, **kwargs: _P.kwargs) -> int: ...  # pragma: no cover


class WrappedFunctionPool(Protocol):
    """Protocol for the pooled decorator factory."""

    @overload
    def __call__(self, _func: Callable[_P, Awaitable[_R]]) -> AsyncPoolWrappedF[_P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[_P, _R]) -> SyncPoolWrappedF[_P, _R]: ...

    def __call__(  # pragma: no cover
        self,
        _func: Union[
            Callable[_P, Awaitable[_R]],
            Callable[_P, _R],
        ],
    ) -> Union[
        AsyncPoolWrappedF[_P, _R],
        SyncPoolWrappedF[_P, _R],
    ]: ...
