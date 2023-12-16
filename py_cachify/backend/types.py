from typing import Any

from typing_extensions import Protocol


class AsyncClient(Protocol):
    async def get(self, name: str, default: Any = None) -> Any:
        raise NotImplementedError

    async def delete(self, *names: str) -> Any:
        raise NotImplementedError

    async def set(self, name: str, value: Any, ex: int | None = None) -> Any:
        raise NotImplementedError


class SyncClient(Protocol):
    def get(self, name: str, default: Any = None) -> Any:
        raise NotImplementedError

    def delete(self, *names: str) -> Any:
        raise NotImplementedError

    def set(self, name: str, value: Any, ex: int | None = None) -> Any:
        raise NotImplementedError
