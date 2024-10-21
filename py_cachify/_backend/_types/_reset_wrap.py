from typing import Awaitable, Callable, TypeVar, Union

from typing_extensions import ParamSpec, Protocol, overload


_R = TypeVar('_R')
_P = ParamSpec('_P')


class AsyncResetWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    async def reset(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class SyncResetWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, _R]  # pragma: no cover

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    def reset(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class WrappedFunctionReset(Protocol):
    @overload
    def __call__(self, _func: Callable[_P, Awaitable[_R]], /) -> AsyncResetWrappedF[_P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[_P, _R], /) -> SyncResetWrappedF[_P, _R]: ...

    def __call__(  # pragma: no cover
        self,
        _func: Union[
            Callable[_P, Awaitable[_R]],
            Callable[_P, _R],
        ],
    ) -> Union[
        AsyncResetWrappedF[_P, _R],
        SyncResetWrappedF[_P, _R],
    ]: ...
