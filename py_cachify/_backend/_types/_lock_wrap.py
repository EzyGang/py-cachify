from typing import Awaitable, Callable, Union

from typing_extensions import ParamSpec, Protocol, TypeVar, overload


_R = TypeVar('_R')
_P = ParamSpec('_P')


class AsyncLockWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, Awaitable[_R]]  # pragma: no cover

    async def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    async def is_locked(self, *args: _P.args, **kwargs: _P.kwargs) -> bool: ...  # pragma: no cover

    async def release(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class SyncLockWrappedF(Protocol[_P, _R]):
    __wrapped__: Callable[_P, _R]  # pragma: no cover

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R: ...  # pragma: no cover

    def is_locked(self, *args: _P.args, **kwargs: _P.kwargs) -> bool: ...  # pragma: no cover

    def release(self, *args: _P.args, **kwargs: _P.kwargs) -> None: ...  # pragma: no cover


class WrappedFunctionLock(Protocol):
    @overload
    def __call__(self, _func: Callable[_P, Awaitable[_R]]) -> AsyncLockWrappedF[_P, _R]: ...  # type: ignore[overload-overlap]

    @overload
    def __call__(self, _func: Callable[_P, _R]) -> SyncLockWrappedF[_P, _R]: ...

    def __call__(  # pragma: no cover
        self,
        _func: Union[
            Callable[_P, Awaitable[_R]],
            Callable[_P, _R],
        ],
    ) -> Union[
        AsyncLockWrappedF[_P, _R],
        SyncLockWrappedF[_P, _R],
    ]: ...
