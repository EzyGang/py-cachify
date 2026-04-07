import pytest
import redis
from redis.asyncio import Redis as RedisAsync

from py_cachify import Cachify, init_cachify


@pytest.fixture(autouse=True)
def init_cachify_fixture() -> None:
    init_cachify(
        sync_client=redis.Redis.from_url(url='redis://localhost:6379/0'),  # pyright: ignore[reportUnknownMemberType]
        async_client=RedisAsync.from_url(url='redis://localhost:6379/1'),  # pyright: ignore[reportUnknownMemberType]
    )


@pytest.fixture
def cachify_local_in_memory_client() -> Cachify:
    return init_cachify(
        is_global=False,
    )


@pytest.fixture
def cachify_local_redis_second() -> Cachify:
    return init_cachify(
        is_global=False,
        sync_client=redis.Redis.from_url(url='redis://localhost:6379/2'),  # pyright: ignore[reportUnknownMemberType]
        async_client=RedisAsync.from_url(url='redis://localhost:6379/3'),  # pyright: ignore[reportUnknownMemberType]
    )
