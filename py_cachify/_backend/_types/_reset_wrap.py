from typing import Awaitable, Callable, TypeVar, Union

from typing_extensions import Concatenate, ParamSpec, Protocol, Self, overload


_R = TypeVar('_R')
_P = ParamSpec('_P')
_S = TypeVar('_S')
_S_co = TypeVar('_S_co', covariant=True)


class AsyncResetWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    async def reset(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class _AsyncResetWrappedFM(Protocol[_S_co, _P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover
    reset: Callable[Concatenate[_S_co, _P], Awaitable[None]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover


class AsyncResetWrappedM(Protocol[_S, _P, _R]):
    __wrapped__: Callable[Concatenate[_S, _P], Awaitable[_R]]  # pragma: no cover
    __call__: Callable[Concatenate[_S, _P], Awaitable[_R]]  # pragma: no cover

    @overload
    def __get__(
        self, instance: _S, owner: Union[type, None] = ..., /
    ) -> _AsyncResetWrappedFM[_S, _P, _R]: ...  # pragma: no cover

    @overload
    def __get__(self, instance: None, owner: Union[type, None] = ..., /) -> Self: ...  # pragma: no cover

    async def reset(self, _self: _S, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class SyncResetWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, _R]  # pragma: no cover

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    def reset(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class _SyncResetWrappedFM(Protocol[_S_co, _P, _R]):
    __wrapped__: Callable[_P, _R]  # pragma: no cover
    reset: Callable[Concatenate[_S_co, _P], None]  # pragma: no cover

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover


class SyncResetWrappedM(Protocol[_S, _P, _R]):
    __wrapped__: Callable[Concatenate[_S, _P], _R]  # pragma: no cover
    __call__: Callable[Concatenate[_S, _P], _R]  # pragma: no cover

    @overload
    def __get__(
        self, instance: _S, owner: Union[type, None] = ..., /
    ) -> _SyncResetWrappedFM[_S, _P, _R]: ...  # pragma: no cover

    @overload
    def __get__(self, instance: None, owner: Union[type, None] = ..., /) -> Self: ...  # pragma: no cover

    def reset(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class WrappedFunctionReset(Protocol):
    @overload
    def __call__(self, _func: Callable[Concatenate[_S, _P], Awaitable[_R]], /) -> AsyncResetWrappedM[_S, _P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[Concatenate[_S, _P], _R], /) -> SyncResetWrappedM[_S, _P, _R]: ...

    @overload
    def __call__(self, _func: Callable[_P, Awaitable[_R]], /) -> AsyncResetWrappedF[_P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[_P, _R], /) -> SyncResetWrappedF[_P, _R]: ...

    def __call__(  # type: ignore[misc]  # pragma: no cover
        self,
        _func: Union[
            Callable[Concatenate[_S, _P], Awaitable[_R]],
            Callable[Concatenate[_S, _P], _R],
            Callable[_P, Awaitable[_R]],
            Callable[_P, _R],
        ],
    ) -> Union[
        AsyncResetWrappedM[_S, _P, _R],
        AsyncResetWrappedF[_P, _R],
        SyncResetWrappedM[_S, _P, _R],
        SyncResetWrappedF[_P, _R],
    ]: ...
