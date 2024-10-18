from typing import Awaitable, Callable, Union

from typing_extensions import Concatenate, ParamSpec, Protocol, Self, TypeVar, overload


_R = TypeVar('_R')
_P = ParamSpec('_P')
_S = TypeVar('_S')
_S_co = TypeVar('_S_co', covariant=True)


class AsyncLockWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    async def is_locked(self, *args: _P.args, **kwargs: _P.kwargs) -> bool: ...  # pragma: no cover

    async def release(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class _AsyncLockWrappedFM(Protocol[_S_co, _P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover
    is_locked: Callable[Concatenate[_S_co, _P], Awaitable[bool]]  # pragma: no cover
    release: Callable[Concatenate[_S_co, _P], Awaitable[None]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover


class AsyncLockWrappedM(Protocol[_S, _P, _R]):
    __wrapped__: Callable[Concatenate[_S, _P], Awaitable[_R]]  # pragma: no cover
    __call__: Callable[Concatenate[_S, _P], Awaitable[_R]]  # pragma: no cover

    @overload
    def __get__(
        self, instance: _S, owner: Union[type, None] = ..., /
    ) -> _AsyncLockWrappedFM[_S, _P, _R]: ...  # pragma: no cover

    @overload
    def __get__(self, instance: None, owner: Union[type, None] = ..., /) -> Self: ...  # pragma: no cover

    async def is_locked(self, *args: _P.args, **kwargs: _P.kwargs) -> bool: ...  # pragma: no cover

    async def release(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class SyncLockWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, _R]

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    def is_locked(self, *args: _P.args, **kwargs: _P.kwargs) -> bool: ...  # pragma: no cover

    def release(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class _SyncLockWrappedFM(Protocol[_S_co, _P, _R]):
    __wrapped__: Callable[_P, _R]  # pragma: no cover
    is_locked: Callable[Concatenate[_S_co, _P], bool]  # pragma: no cover
    release: Callable[Concatenate[_S_co, _P], None]  # pragma: no cover

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover


class SyncLockWrappedM(Protocol[_S, _P, _R]):
    __wrapped__: Callable[Concatenate[_S, _P], _R]  # pragma: no cover
    __call__: Callable[Concatenate[_S, _P], _R]  # pragma: no cover

    @overload
    def __get__(
        self, instance: _S, owner: Union[type, None] = ..., /
    ) -> _SyncLockWrappedFM[_S, _P, _R]: ...  # pragma: no cover

    @overload
    def __get__(self, instance: None, owner: Union[type, None] = ..., /) -> Self: ...  # pragma: no cover

    def is_locked(self, *args: _P.args, **kwargs: _P.kwargs) -> bool: ...  # pragma: no cover

    def release(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class WrappedFunctionLock(Protocol):
    @overload
    def __call__(self, _func: Callable[Concatenate[_S, _P], Awaitable[_R]], /) -> AsyncLockWrappedM[_S, _P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[Concatenate[_S, _P], _R], /) -> SyncLockWrappedM[_S, _P, _R]: ...

    @overload
    def __call__(self, _func: Callable[_P, Awaitable[_R]], /) -> AsyncLockWrappedF[_P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[_P, _R], /) -> SyncLockWrappedF[_P, _R]: ...

    def __call__(  # type: ignore[misc]  # pragma: no cover
        self,
        _func: Union[
            Callable[Concatenate[_S, _P], Awaitable[_R]],
            Callable[Concatenate[_S, _P], _R],
            Callable[_P, Awaitable[_R]],
            Callable[_P, _R],
        ],
    ) -> Union[
        AsyncLockWrappedM[_S, _P, _R],
        AsyncLockWrappedF[_P, _R],
        SyncLockWrappedM[_S, _P, _R],
        SyncLockWrappedF[_P, _R],
    ]: ...
