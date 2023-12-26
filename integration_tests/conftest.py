import pytest
import redis

from py_cachify import init_cachify


@pytest.fixture(autouse=True)
def init_cachify_fixture():
    init_cachify(
        sync_client=redis.from_url(url='redis://localhost:6379/0'),
        async_client=redis.asyncio.from_url(url='redis://localhost:6379/1'),
    )
