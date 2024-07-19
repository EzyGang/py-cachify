from __future__ import annotations

from typing import Any, Awaitable, Protocol, Union


class AsyncClient(Protocol):
    def get(self, name: str) -> Awaitable[Any]:
        raise NotImplementedError

    def delete(self, *names: str) -> Awaitable[Any]:
        raise NotImplementedError

    def set(self, name: str, value: Any, ex: Union[int, None] = None) -> Awaitable[Any]:
        raise NotImplementedError


class SyncClient(Protocol):
    def get(self, name: str) -> Any | None:
        raise NotImplementedError

    def delete(self, *names: str) -> Any:
        raise NotImplementedError

    def set(self, name: str, value: Any, ex: Union[int, None] = None) -> Any:
        raise NotImplementedError
