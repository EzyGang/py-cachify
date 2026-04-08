import pytest
import pytest_asyncio
import redis
from redis.asyncio import Redis as RedisAsync

from py_cachify import Cachify, init_cachify


@pytest_asyncio.fixture(autouse=True)  # pyright: ignore[reportUnknownMemberType]
async def init_cachify_fixture() -> None:
    sync_client = redis.Redis.from_url(url='redis://localhost:6379/0')  # pyright: ignore[reportUnknownMemberType]
    async_client = RedisAsync.from_url(url='redis://localhost:6379/1')  # pyright: ignore[reportUnknownMemberType]

    init_cachify(
        sync_client=sync_client,
        async_client=async_client,
    )


@pytest.fixture
def cachify_local_in_memory_client() -> Cachify:
    return init_cachify(
        is_global=False,
    )


@pytest_asyncio.fixture  # pyright: ignore[reportUnknownMemberType]
async def cachify_local_redis_second() -> Cachify:
    async_client = RedisAsync.from_url(url='redis://localhost:6379/3')  # pyright: ignore[reportUnknownMemberType]
    sync_client = redis.Redis.from_url(url='redis://localhost:6379/2')  # pyright: ignore[reportUnknownMemberType]

    return init_cachify(
        is_global=False,
        sync_client=sync_client,
        async_client=async_client,
    )
