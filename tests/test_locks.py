import pytest

from py_cachify.exceptions import CachifyLockError
from py_cachify.lock import async_lock, lock


@pytest.mark.asyncio
async def test_async_lock(init_cachify_fixture):
    async def async_operation():
        async with async_lock('lock'):
            return None

    await async_operation()


@pytest.mark.asyncio
async def test_async_lock_already_locked(init_cachify_fixture):
    key = 'lock'

    async def async_operation():
        async with async_lock(key):
            async with async_lock(key):
                pass

    with pytest.raises(CachifyLockError, match=f'{key} is already locked!'):
        await async_operation()


def test_lock(init_cachify_fixture):
    def sync_operation():
        with lock('lock'):
            pass

    sync_operation()


def test_lock_already_locked(init_cachify_fixture):
    key = 'lock'

    def sync_operation():
        with lock(key):
            with lock(key):
                pass

    with pytest.raises(CachifyLockError, match=f'{key} is already locked!'):
        sync_operation()
