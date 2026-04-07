# pyright: reportPrivateUsage=false
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread
from time import sleep
from typing import Any

import pytest
from pytest_mock import MockerFixture

from py_cachify import Cachify, CachifyPoolFullError, init_cachify, pool, pooled
from py_cachify._backend._lib import get_cachify_client


# =============================================================================
# Context Manager Tests
# =============================================================================


def test_pool_context_manager_sync_basic(init_cachify_fixture: Any) -> None:
    """Test basic sync context manager acquire and release."""
    test_pool = pool(key='test-pool-sync', max_size=2)

    with test_pool:
        assert test_pool.size() == 1

    # After exiting context, pool should be empty
    assert test_pool.size() == 0


@pytest.mark.asyncio
async def test_pool_context_manager_async_basic(init_cachify_fixture: Any) -> None:
    """Test basic async context manager acquire and release."""
    test_pool = pool(key='test-pool-async', max_size=2)

    async with test_pool:
        assert await test_pool.asize() == 1

    # After exiting context, pool should be empty
    assert await test_pool.asize() == 0


def test_pool_context_manager_sync_multiple_acquire(init_cachify_fixture: Any) -> None:
    """Test acquiring multiple slots up to max_size synchronously."""
    test_pool = pool(key='test-pool-multi', max_size=3)
    acquired_slots: list[Any] = []

    def acquire_slot() -> None:
        with test_pool:
            acquired_slots.append(test_pool.size())
            sleep(0.2)  # Hold the slot briefly

    # Start 3 threads that each acquire a slot
    threads = [Thread(target=acquire_slot) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All slots should have been acquired
    assert len(acquired_slots) == 3
    assert all(size >= 1 for size in acquired_slots)


@pytest.mark.asyncio
async def test_pool_context_manager_async_multiple_acquire(init_cachify_fixture: Any) -> None:
    """Test acquiring multiple slots up to max_size asynchronously."""
    test_pool = pool(key='test-pool-multi-async', max_size=3)
    acquired_sizes: list[Any] = []

    async def acquire_slot() -> None:
        async with test_pool:
            size = await test_pool.asize()
            acquired_sizes.append(size)
            await asyncio.sleep(0.2)  # Hold the slot briefly

    # Start 3 concurrent tasks
    await asyncio.gather(*[acquire_slot() for _ in range(3)])

    # All slots should have been acquired
    assert len(acquired_sizes) == 3
    assert all(size >= 1 for size in acquired_sizes)


def test_pool_context_manager_sync_full_raises(init_cachify_fixture: Any) -> None:
    """Test that sync context manager raises when pool is full."""
    test_pool = pool(key='test-pool-full', max_size=1)

    def hold_slot() -> None:
        with test_pool:
            sleep(1)  # Hold the slot

    # Start a thread that holds the slot
    thread = Thread(target=hold_slot)
    thread.start()
    sleep(0.1)  # Let the first thread acquire the slot

    try:
        # Second acquisition should raise CachifyPoolFullError
        with pytest.raises(CachifyPoolFullError):
            with test_pool:
                pass
    finally:
        thread.join()


@pytest.mark.asyncio
async def test_pool_context_manager_async_full_raises(init_cachify_fixture: Any) -> None:
    """Test that async context manager raises when pool is full."""
    test_pool = pool(key='test-pool-full-async', max_size=1)

    async def hold_slot() -> None:
        async with test_pool:
            await asyncio.sleep(1)  # Hold the slot

    # Start a task that holds the slot
    task = asyncio.create_task(hold_slot())
    await asyncio.sleep(0.1)  # Let the first task acquire the slot

    try:
        # Second acquisition should raise CachifyPoolFullError
        with pytest.raises(CachifyPoolFullError):
            async with test_pool:
                pass
    finally:
        await task


def test_pool_size_method_sync(init_cachify_fixture: Any) -> None:
    """Test sync pool.size() method."""
    test_pool = pool(key='test-pool-size', max_size=2)

    assert test_pool.size() == 0  # Initially empty

    with test_pool:
        assert test_pool.size() == 1

    assert test_pool.size() == 0  # After release


@pytest.mark.asyncio
async def test_pool_asize_method_async(init_cachify_fixture: Any) -> None:
    """Test async pool.asize() method."""
    test_pool = pool(key='test-pool-asize', max_size=2)

    assert await test_pool.asize() == 0  # Initially empty

    async with test_pool:
        assert await test_pool.asize() == 1

    assert await test_pool.asize() == 0  # After release


# =============================================================================
# Decorator via pool().pooled() Tests
# =============================================================================


def test_pool_instance_decorator_sync_basic(init_cachify_fixture: Any) -> None:
    """Test basic sync decorator via pool().pooled()."""
    test_pool = pool(key='test-decorator-pool', max_size=2)
    call_count = 0

    @test_pool.pooled()
    def process_task(task_id: int) -> int:
        nonlocal call_count
        call_count += 1
        sleep(0.1)
        return task_id * 10

    result = process_task(5)
    assert result == 50
    assert call_count == 1


@pytest.mark.asyncio
async def test_pool_instance_decorator_async_basic(init_cachify_fixture: Any) -> None:
    """Test basic async decorator via pool().pooled()."""
    test_pool = pool(key='test-decorator-pool-async', max_size=2)
    call_count = 0

    @test_pool.pooled()
    async def process_task(task_id: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return task_id * 10

    result = await process_task(5)
    assert result == 50
    assert call_count == 1


def test_pool_instance_decorator_sync_concurrent(init_cachify_fixture: Any) -> None:
    """Test sync decorator with concurrent calls respecting max_size."""
    test_pool = pool(key='test-decorator-concurrent', max_size=2)
    active_count = 0
    max_observed = 0
    completed_tasks: list[Any] = []

    @test_pool.pooled(on_full=lambda task_id: completed_tasks.append(f'queued-{task_id}'))
    def process_task(task_id: int) -> str:
        nonlocal active_count, max_observed
        active_count += 1
        max_observed = max(max_observed, active_count)
        sleep(0.3)  # Hold slot
        active_count -= 1
        completed_tasks.append(f'done-{task_id}')
        return f'task-{task_id}'

    # Start 4 concurrent calls with max_size=2
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(process_task, i) for i in range(4)]
        _ = [f.result() for f in as_completed(futures)]

    # Check max concurrent never exceeded 2
    assert max_observed <= 2
    # All tasks should have completed (either done or queued)
    assert len(completed_tasks) == 4
    # Some should be done (executed), some should be queued
    # Timing-dependent, so we just verify the constraints are respected
    done_count = sum(1 for t in completed_tasks if t.startswith('done-'))
    queued_count = sum(1 for t in completed_tasks if t.startswith('queued-'))
    assert done_count >= 1
    assert queued_count >= 1
    assert done_count + queued_count == 4


@pytest.mark.asyncio
async def test_pool_instance_decorator_async_concurrent(init_cachify_fixture: Any) -> None:
    """Test async decorator with concurrent calls respecting max_size."""
    test_pool = pool(key='test-decorator-concurrent-async', max_size=2)
    active_count = 0
    max_observed = 0
    completed_tasks: list[Any] = []

    async def handle_full(task_id: int) -> str:
        completed_tasks.append(f'queued-{task_id}')
        return f'queued-{task_id}'

    @test_pool.pooled(on_full=handle_full)
    async def process_task(task_id: int) -> str:
        nonlocal active_count, max_observed
        active_count += 1
        max_observed = max(max_observed, active_count)
        await asyncio.sleep(0.3)  # Hold slot
        active_count -= 1
        completed_tasks.append(f'done-{task_id}')
        return f'task-{task_id}'

    # Start 4 concurrent calls with max_size=2
    tasks = [asyncio.create_task(process_task(i)) for i in range(4)]
    _ = await asyncio.gather(*tasks)

    # Check max concurrent never exceeded 2
    assert max_observed <= 2
    # All tasks should have completed (either done or queued)
    assert len(completed_tasks) == 4
    # Some should be done (executed), some should be queued
    # Timing-dependent in async context, so we just verify constraints
    done_count = sum(1 for t in completed_tasks if t.startswith('done-'))
    queued_count = sum(1 for t in completed_tasks if t.startswith('queued-'))
    assert done_count >= 1
    assert queued_count >= 1
    assert done_count + queued_count == 4


def test_pool_instance_decorator_sync_on_full_callback(init_cachify_fixture: Any) -> None:
    """Test sync decorator on_full callback when pool is full."""
    test_pool = pool(key='test-decorator-onfull', max_size=1)
    on_full_called = False
    on_full_args = None

    def handle_full(task_id: int) -> str:
        nonlocal on_full_called, on_full_args
        on_full_called = True
        on_full_args = task_id
        return 'FULL'

    @test_pool.pooled(on_full=handle_full)
    def process_task(task_id: int) -> int:
        sleep(0.5)  # Hold slot
        return task_id

    def caller(task_id: int) -> Any:
        return process_task(task_id)

    # Start 2 threads - one will get the slot, one will trigger on_full
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(caller, 1)
        sleep(0.1)  # Let first acquire
        future2 = executor.submit(caller, 2)

        results = [future1.result(), future2.result()]

    assert 1 in results  # The one that got the slot
    assert 'FULL' in results  # The one that triggered on_full
    assert on_full_called is True
    assert on_full_args == 2


@pytest.mark.asyncio
async def test_pool_instance_decorator_async_on_full_callback(init_cachify_fixture: Any) -> None:
    """Test async decorator on_full callback when pool is full."""
    test_pool = pool(key='test-decorator-onfull-async', max_size=1)
    on_full_called = False
    on_full_args = None

    async def handle_full(task_id: int) -> str:
        nonlocal on_full_called, on_full_args
        on_full_called = True
        on_full_args = task_id
        return 'FULL'

    @test_pool.pooled(on_full=handle_full)
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.5)  # Hold slot
        return task_id

    # Start 2 tasks - one will get the slot, one will trigger on_full
    task1 = asyncio.create_task(process_task(1))
    await asyncio.sleep(0.1)  # Let first acquire
    task2 = asyncio.create_task(process_task(2))

    results = await asyncio.gather(task1, task2)

    assert 1 in results  # The one that got the slot
    assert 'FULL' in results  # The one that triggered on_full
    assert on_full_called is True
    assert on_full_args == 2


def test_pool_instance_decorator_sync_raise_on_full(init_cachify_fixture: Any) -> None:
    """Test sync decorator raise_on_full=True raises exception."""
    test_pool = pool(key='test-decorator-raise', max_size=1)

    @test_pool.pooled(raise_on_full=True)
    def process_task(task_id: int) -> int:
        sleep(0.5)  # Hold slot
        return task_id

    def caller(task_id: int) -> Any:
        try:
            return process_task(task_id)
        except CachifyPoolFullError:
            return 'RAISED'

    # Start 2 threads - one will get the slot, one will raise
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(caller, 1)
        sleep(0.1)  # Let first acquire
        future2 = executor.submit(caller, 2)

        results = [future1.result(), future2.result()]

    assert 1 in results  # The one that got the slot
    assert 'RAISED' in results  # The one that raised


@pytest.mark.asyncio
async def test_pool_instance_decorator_async_raise_on_full(init_cachify_fixture: Any) -> None:
    """Test async decorator raise_on_full=True raises exception."""
    test_pool = pool(key='test-decorator-raise-async', max_size=1)

    @test_pool.pooled(raise_on_full=True)
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.5)  # Hold slot
        return task_id

    async def caller(task_id: int) -> Any:
        try:
            return await process_task(task_id)
        except CachifyPoolFullError:
            return 'RAISED'

    # Start 2 tasks - one will get the slot, one will raise
    task1 = asyncio.create_task(caller(1))
    await asyncio.sleep(0.1)  # Let first acquire
    task2 = asyncio.create_task(caller(2))

    results = await asyncio.gather(task1, task2)

    assert 1 in results  # The one that got the slot
    assert 'RAISED' in results  # The one that raised


def test_pool_instance_decorator_sync_returns_none_when_full(init_cachify_fixture: Any) -> None:
    """Test sync decorator returns None when pool is full and no on_full callback."""
    test_pool = pool(key='test-decorator-none', max_size=1)

    @test_pool.pooled()  # No on_full, raise_on_full=False (default)
    def process_task(task_id: int) -> int:
        sleep(0.5)  # Hold slot
        return task_id

    def caller(task_id: int) -> Any:
        return process_task(task_id)

    # Start 2 threads - one will get the slot, one will return None
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(caller, 1)
        sleep(0.1)  # Let first acquire
        future2 = executor.submit(caller, 2)

        results = [future1.result(), future2.result()]

    assert 1 in results  # The one that got the slot
    assert None in results  # The one that returned None


@pytest.mark.asyncio
async def test_pool_instance_decorator_async_returns_none_when_full(init_cachify_fixture: Any) -> None:
    """Test async decorator returns None when pool is full and no on_full callback."""
    test_pool = pool(key='test-decorator-none-async', max_size=1)

    @test_pool.pooled()  # No on_full, raise_on_full=False (default)
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.5)  # Hold slot
        return task_id

    # Start 2 tasks - one will get the slot, one will return None
    task1 = asyncio.create_task(process_task(1))
    await asyncio.sleep(0.1)  # Let first acquire
    task2 = asyncio.create_task(process_task(2))

    results = await asyncio.gather(task1, task2)

    assert 1 in results  # The one that got the slot
    assert None in results  # The one that returned None


def test_pool_instance_decorator_sync_size_method(init_cachify_fixture: Any) -> None:
    """Test sync decorated function has size() method."""
    test_pool = pool(key='test-decorator-size', max_size=2)

    @test_pool.pooled()
    def process_task(task_id: int) -> int:
        sleep(0.1)
        return task_id

    # size() should return 0 when no slots are acquired
    assert process_task.size(1) == 0

    # After calling, size might be 0 (since function completes quickly)
    process_task(1)


@pytest.mark.asyncio
async def test_pool_instance_decorator_async_size_method(init_cachify_fixture: Any) -> None:
    """Test async decorated function has size() method."""
    test_pool = pool(key='test-decorator-size-async', max_size=2)

    @test_pool.pooled()
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.1)
        return task_id

    # size() should return 0 when no slots are acquired
    assert await process_task.size(1) == 0

    # After calling, size might be 0 (since function completes quickly)
    await process_task(1)


# =============================================================================
# Standalone pooled() Decorator Tests
# =============================================================================


def test_standalone_pooled_sync_basic(init_cachify_fixture: Any) -> None:
    """Test basic sync standalone pooled() decorator."""
    call_count = 0

    @pooled(key='standalone-pool-{task_id}', max_size=2)
    def process_task(task_id: int) -> int:
        nonlocal call_count
        call_count += 1
        sleep(0.1)
        return task_id * 10

    result = process_task(5)
    assert result == 50
    assert call_count == 1


@pytest.mark.asyncio
async def test_standalone_pooled_async_basic(init_cachify_fixture: Any) -> None:
    """Test basic async standalone pooled() decorator."""
    call_count = 0

    @pooled(key='standalone-pool-async-{task_id}', max_size=2)
    async def process_task(task_id: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return task_id * 10

    result = await process_task(5)
    assert result == 50
    assert call_count == 1


def test_standalone_pooled_sync_dynamic_key(init_cachify_fixture: Any) -> None:
    """Test that standalone pooled() creates different pools based on dynamic keys."""
    completed_tasks: list[Any] = []

    @pooled(
        key='dynamic-pool-{user_id}',
        max_size=1,
        on_full=lambda user_id, task_id: completed_tasks.append(f'queued-{user_id}-{task_id}'),
    )
    def process_for_user(user_id: str, task_id: int) -> str:
        sleep(0.2)
        completed_tasks.append(f'done-{user_id}-{task_id}')
        return f'{user_id}-{task_id}'

    # user_id='alice' and user_id='bob' should have separate pools
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(process_for_user, 'alice', 1),
            executor.submit(process_for_user, 'alice', 2),  # Same pool, may be blocked
            executor.submit(process_for_user, 'bob', 1),  # Different pool
            executor.submit(process_for_user, 'bob', 2),  # Different pool, may be blocked
        ]
        _ = [f.result() for f in as_completed(futures)]

    # All 4 tasks should be accounted for
    assert len(completed_tasks) == 4
    # Each user should have 1 done and 1 queued
    assert sum(1 for t in completed_tasks if t == 'done-alice-1' or t == 'done-alice-2') == 1
    assert sum(1 for t in completed_tasks if t == 'done-bob-1' or t == 'done-bob-2') == 1
    assert sum(1 for t in completed_tasks if t.startswith('queued-alice')) == 1
    assert sum(1 for t in completed_tasks if t.startswith('queued-bob')) == 1


@pytest.mark.asyncio
async def test_standalone_pooled_async_dynamic_key(init_cachify_fixture: Any) -> None:
    """Test that async standalone pooled() creates different pools based on dynamic keys."""
    completed_tasks: list[Any] = []

    async def handle_full(user_id: str, task_id: int) -> str:
        completed_tasks.append(f'queued-{user_id}-{task_id}')
        return f'queued-{user_id}-{task_id}'

    @pooled(key='dynamic-pool-async-{user_id}', max_size=1, on_full=handle_full)
    async def process_for_user(user_id: str, task_id: int) -> str:
        await asyncio.sleep(0.2)
        completed_tasks.append(f'done-{user_id}-{task_id}')
        return f'{user_id}-{task_id}'

    # user_id='alice' and user_id='bob' should have separate pools
    tasks = [
        asyncio.create_task(process_for_user('alice', 1)),
        asyncio.create_task(process_for_user('alice', 2)),  # Same pool, may be blocked
        asyncio.create_task(process_for_user('bob', 1)),  # Different pool
        asyncio.create_task(process_for_user('bob', 2)),  # Different pool, may be blocked
    ]
    _ = await asyncio.gather(*tasks)

    # All 4 tasks should be accounted for
    assert len(completed_tasks) == 4
    # Each user should have 1 done and 1 queued
    assert sum(1 for t in completed_tasks if t == 'done-alice-1' or t == 'done-alice-2') == 1
    assert sum(1 for t in completed_tasks if t == 'done-bob-1' or t == 'done-bob-2') == 1
    assert sum(1 for t in completed_tasks if t.startswith('queued-alice')) == 1
    assert sum(1 for t in completed_tasks if t.startswith('queued-bob')) == 1


def test_standalone_pooled_sync_on_full(init_cachify_fixture: Any) -> None:
    """Test standalone pooled() sync on_full callback."""
    on_full_calls: list[Any] = []

    def handle_full(task_id: int) -> str:
        on_full_calls.append(task_id)
        return f'FULL-{task_id}'

    @pooled(key='standalone-onfull', max_size=1, on_full=handle_full)
    def process_task(task_id: int) -> int:
        sleep(0.5)
        return task_id

    def caller(task_id: int) -> Any:
        return process_task(task_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(caller, 1)
        sleep(0.1)
        future2 = executor.submit(caller, 2)
        results = [future1.result(), future2.result()]

    assert 1 in results
    assert 'FULL-2' in results
    assert 2 in on_full_calls


@pytest.mark.asyncio
async def test_standalone_pooled_async_on_full(init_cachify_fixture: Any) -> None:
    """Test standalone pooled() async on_full callback."""
    on_full_calls: list[Any] = []

    async def handle_full(task_id: int) -> str:
        on_full_calls.append(task_id)
        return f'FULL-{task_id}'

    @pooled(key='standalone-onfull-async', max_size=1, on_full=handle_full)
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.5)
        return task_id

    task1 = asyncio.create_task(process_task(1))
    await asyncio.sleep(0.1)
    task2 = asyncio.create_task(process_task(2))
    results = await asyncio.gather(task1, task2)

    assert 1 in results
    assert 'FULL-2' in results
    assert 2 in on_full_calls


def test_standalone_pooled_sync_raise_on_full(init_cachify_fixture: Any) -> None:
    """Test standalone pooled() sync raise_on_full=True."""

    @pooled(key='standalone-raise', max_size=1, raise_on_full=True)
    def process_task(task_id: int) -> int:
        sleep(0.5)
        return task_id

    def caller(task_id: int) -> Any:
        try:
            return process_task(task_id)
        except CachifyPoolFullError:
            return 'RAISED'

    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(caller, 1)
        sleep(0.1)
        future2 = executor.submit(caller, 2)
        results = [future1.result(), future2.result()]

    assert 1 in results
    assert 'RAISED' in results


@pytest.mark.asyncio
async def test_standalone_pooled_async_raise_on_full(init_cachify_fixture: Any) -> None:
    """Test standalone pooled() async raise_on_full=True."""

    @pooled(key='standalone-raise-async', max_size=1, raise_on_full=True)
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.5)
        return task_id

    async def caller(task_id: int) -> Any:
        try:
            return await process_task(task_id)
        except CachifyPoolFullError:
            return 'RAISED'

    task1 = asyncio.create_task(caller(1))
    await asyncio.sleep(0.1)
    task2 = asyncio.create_task(caller(2))
    results = await asyncio.gather(task1, task2)

    assert 1 in results
    assert 'RAISED' in results


def test_standalone_pooled_sync_size_method(init_cachify_fixture: Any) -> None:
    """Test standalone pooled() sync size() method."""

    @pooled(key='standalone-size-{user_id}', max_size=2)
    def process_task(user_id: str, task_id: int) -> str:
        sleep(0.1)
        return f'{user_id}-{task_id}'

    # size() should return 0 when pool is empty
    assert process_task.size('alice', 1) == 0

    # After calling, size might be 0 (since function completes quickly)
    process_task('alice', 1)


@pytest.mark.asyncio
async def test_standalone_pooled_async_size_method(init_cachify_fixture: Any) -> None:
    """Test standalone pooled() async size() method."""

    @pooled(key='standalone-size-async-{user_id}', max_size=2)
    async def process_task(user_id: str, task_id: int) -> str:
        await asyncio.sleep(0.1)
        return f'{user_id}-{task_id}'

    # size() should return 0 when pool is empty
    assert await process_task.size('alice', 1) == 0

    # After calling, size might be 0 (since function completes quickly)
    await process_task('alice', 1)


# =============================================================================
# Cachify Class Method Tests
# =============================================================================


def test_cachify_pool_method_sync(init_cachify_fixture: Any) -> None:
    """Test Cachify.pool() method returns a usable pool instance."""
    cachify = init_cachify(is_global=False)

    test_pool = cachify.pool(key='cachify-pool-method', max_size=2)

    with test_pool:
        assert test_pool.size() == 1

    assert test_pool.size() == 0


@pytest.mark.asyncio
async def test_cachify_pool_method_async(init_cachify_fixture: Any) -> None:
    """Test Cachify.pool() method returns a usable async pool instance."""
    cachify = init_cachify(is_global=False)

    test_pool = cachify.pool(key='cachify-pool-method-async', max_size=2)

    async with test_pool:
        assert await test_pool.asize() == 1

    assert await test_pool.asize() == 0


def test_cachify_pooled_method_sync(init_cachify_fixture: Any) -> None:
    """Test Cachify.pooled() decorator method."""
    cachify = init_cachify(is_global=False)
    call_count = 0

    @cachify.pooled(key='cachify-pooled-{task_id}', max_size=2)
    def process_task(task_id: int) -> int:
        nonlocal call_count
        call_count += 1
        sleep(0.1)
        return task_id * 10

    result = process_task(3)
    assert result == 30
    assert call_count == 1


@pytest.mark.asyncio
async def test_cachify_pooled_method_async(init_cachify_fixture: Any) -> None:
    """Test Cachify.pooled() async decorator method."""
    cachify = init_cachify(is_global=False)
    call_count = 0

    @cachify.pooled(key='cachify-pooled-async-{task_id}', max_size=2)
    async def process_task(task_id: int) -> int:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return task_id * 10

    result = await process_task(3)
    assert result == 30
    assert call_count == 1


# =============================================================================
# Client Isolation Tests
# =============================================================================


def test_pool_client_isolation_sync(
    cachify_local_redis_second: Cachify,
) -> None:
    """Test that pools with same key on different clients are isolated."""
    global_pool = pool(key='isolated-pool', max_size=1)
    local_pool = cachify_local_redis_second.pool(key='isolated-pool', max_size=1)

    # Both pools have same key but different backends
    with global_pool:
        # Global pool has 1 slot occupied
        assert global_pool.size() == 1
        # Local pool should be empty (different backend)
        assert local_pool.size() == 0

        with local_pool:
            # Local pool can also have 1 slot
            assert local_pool.size() == 1


@pytest.mark.asyncio
async def test_pool_client_isolation_async(
    cachify_local_redis_second: Cachify,
) -> None:
    """Test that async pools with same key on different clients are isolated."""
    global_pool = pool(key='isolated-pool-async', max_size=1)
    local_pool = cachify_local_redis_second.pool(key='isolated-pool-async', max_size=1)

    # Both pools have same key but different backends
    async with global_pool:
        # Global pool has 1 slot occupied
        assert await global_pool.asize() == 1
        # Local pool should be empty (different backend)
        assert await local_pool.asize() == 0

        async with local_pool:
            # Local pool can also have 1 slot
            assert await local_pool.asize() == 1


def test_pooled_decorator_client_isolation_sync(
    cachify_local_redis_second: Cachify,
    mocker: MockerFixture,
) -> None:
    """Test that pooled decorators on different clients are isolated."""
    global_calls: list[Any] = []
    local_calls: list[Any] = []

    @pooled(key='isolated-decorator', max_size=1)
    def global_task(task_id: int) -> str:
        global_calls.append(task_id)
        sleep(0.2)
        return f'global-{task_id}'

    @cachify_local_redis_second.pooled(key='isolated-decorator', max_size=1)
    def local_task(task_id: int) -> str:
        local_calls.append(task_id)
        sleep(0.2)
        return f'local-{task_id}'

    # Both can run concurrently since they use different backends
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(global_task, 1)
        future2 = executor.submit(local_task, 1)
        results = sorted([f.result() for f in as_completed([future1, future2])])

    assert results == ['global-1', 'local-1']
    assert len(global_calls) == 1
    assert len(local_calls) == 1


# =============================================================================
# Slot Expiration and TTL Tests
# =============================================================================


def test_pool_slot_expiration_sync(init_cachify_fixture: Any) -> None:
    """Test that pool slots expire after slot_exp time."""
    test_pool = pool(key='test-pool-exp', max_size=1, slot_exp=1)

    # Acquire a slot
    with test_pool:
        assert test_pool.size() == 1

    # Slot should be released after context exit
    assert test_pool.size() == 0

    # Simulate a stuck slot by directly manipulating state
    cachify = get_cachify_client()
    from py_cachify._backend._pool_state import PoolState

    state = PoolState()
    import time

    # Create an already-expired slot
    state.slots['stuck-slot'] = time.time() - 1  # Expired 1 second ago
    cachify.set(key='test-pool-exp-state', val=state)

    # Now the pool should cleanup the expired slot on next access
    # and allow new acquisitions
    with test_pool:
        assert test_pool.size() == 1


@pytest.mark.asyncio
async def test_pool_slot_expiration_async(init_cachify_fixture: Any) -> None:
    """Test that async pool slots expire after slot_exp time."""
    test_pool = pool(key='test-pool-exp-async', max_size=1, slot_exp=1)

    # Acquire a slot
    async with test_pool:
        assert await test_pool.asize() == 1

    # Slot should be released after context exit
    assert await test_pool.asize() == 0


def test_default_pool_slot_expiration_from_init_cachify(init_cachify_fixture: Any) -> None:
    """Test that default_pool_slot_expiration is used from init_cachify."""
    cachify = init_cachify(default_pool_slot_expiration=300, is_global=False)

    test_pool = cachify.pool(key='test-default-exp', max_size=2)

    # Pool should use the default from cachify
    assert test_pool._get_slot_expiration() == 300


def test_pool_slot_exp_override_default(init_cachify_fixture: Any) -> None:
    """Test that slot_exp parameter overrides default from init_cachify."""
    cachify = init_cachify(default_pool_slot_expiration=300, is_global=False)

    test_pool = cachify.pool(key='test-override-exp', max_size=2, slot_exp=60)

    # Pool should use the explicit slot_exp, not the default
    assert test_pool._get_slot_expiration() == 60


# =============================================================================
# Error Handling Tests
# =============================================================================


def test_pool_release_on_exception_sync(init_cachify_fixture: Any) -> None:
    """Test that sync pool releases slot even when exception occurs."""
    test_pool = pool(key='test-pool-exception', max_size=1)

    try:
        with test_pool:
            assert test_pool.size() == 1
            raise ValueError('Test error')
    except ValueError:
        pass

    # Pool should be empty after exception
    assert test_pool.size() == 0


@pytest.mark.asyncio
async def test_pool_release_on_exception_async(init_cachify_fixture: Any) -> None:
    """Test that async pool releases slot even when exception occurs."""
    test_pool = pool(key='test-pool-exception-async', max_size=1)

    try:
        async with test_pool:
            assert await test_pool.asize() == 1
            raise ValueError('Test error')
    except ValueError:
        pass

    # Pool should be empty after exception
    assert await test_pool.asize() == 0


def test_pool_decorator_release_on_exception_sync(init_cachify_fixture: Any) -> None:
    """Test that sync pool decorator releases slot even when function raises."""
    test_pool = pool(key='test-decorator-exception', max_size=1)

    @test_pool.pooled()
    def failing_task() -> None:
        raise ValueError('Task failed')

    try:
        failing_task()
    except ValueError:
        pass

    # Pool should be empty after exception
    assert test_pool.size() == 0


@pytest.mark.asyncio
async def test_pool_decorator_release_on_exception_async(init_cachify_fixture: Any) -> None:
    """Test that async pool decorator releases slot even when function raises."""
    test_pool = pool(key='test-decorator-exception-async', max_size=1)

    @test_pool.pooled()
    async def failing_task() -> None:
        raise ValueError('Task failed')

    try:
        await failing_task()
    except ValueError:
        pass

    # Pool should be empty after exception
    assert await test_pool.asize() == 0


# =============================================================================
# Edge Cases
# =============================================================================


def test_pool_max_size_1_sync(init_cachify_fixture: Any) -> None:
    """Test pool with max_size=1 only allows single concurrent access."""
    test_pool = pool(key='test-pool-size-1', max_size=1)
    concurrent_count = 0
    max_concurrent = 0
    completed: list[str] = []

    @test_pool.pooled(on_full=lambda task_id: completed.append(f'queued-{task_id}'))
    def exclusive_task(task_id: int) -> str:
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        sleep(0.2)
        concurrent_count -= 1
        completed.append(f'done-{task_id}')
        return f'task-{task_id}'

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(exclusive_task, i) for i in range(3)]
        _ = [f.result() for f in as_completed(futures)]

    # All 3 should be accounted for
    assert len(completed) == 3
    # At least 1 done, at least 1 queued (timing-dependent)
    done_count = sum(1 for c in completed if c.startswith('done-'))
    queued_count = sum(1 for c in completed if c.startswith('queued-'))
    assert done_count >= 1
    assert queued_count >= 1
    assert done_count + queued_count == 3
    # Max concurrent should be 1 (enforced by pool)
    assert max_concurrent == 1


@pytest.mark.asyncio
async def test_pool_max_size_1_async(init_cachify_fixture: Any) -> None:
    """Test async pool with max_size=1 only allows single concurrent access."""
    test_pool = pool(key='test-pool-size-1-async', max_size=1)
    concurrent_count = 0
    max_concurrent = 0
    completed: list[str] = []

    async def handle_full(task_id: int) -> str:
        completed.append(f'queued-{task_id}')
        return f'queued-{task_id}'

    @test_pool.pooled(on_full=handle_full)
    async def exclusive_task(task_id: int) -> str:
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.2)
        concurrent_count -= 1
        completed.append(f'done-{task_id}')
        return f'task-{task_id}'

    tasks = [asyncio.create_task(exclusive_task(i)) for i in range(3)]
    _ = await asyncio.gather(*tasks)

    # All 3 should be accounted for
    assert len(completed) == 3
    # At least 1 done, at least 1 queued (timing-dependent in async)
    done_count = sum(1 for c in completed if c.startswith('done-'))
    queued_count = sum(1 for c in completed if c.startswith('queued-'))
    assert done_count >= 1
    assert queued_count >= 1
    assert done_count + queued_count == 3
    # Max concurrent should be 1 (enforced by pool)
    assert max_concurrent == 1


def test_pool_large_max_size_sync(init_cachify_fixture: Any) -> None:
    """Test pool with large max_size allows many concurrent accesses."""
    test_pool = pool(key='test-pool-large', max_size=10)
    concurrent_count = 0
    max_concurrent = 0

    @test_pool.pooled()
    def concurrent_task(task_id: int) -> int:
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        sleep(0.3)
        concurrent_count -= 1
        return task_id

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(concurrent_task, i) for i in range(10)]
        results = [f.result() for f in as_completed(futures)]

    assert sorted(r for r in results if r is not None) == list(range(10))
    # With max_size=10, we should see significant concurrency
    assert max_concurrent >= 3  # At least some concurrency observed


@pytest.mark.asyncio
async def test_pool_large_max_size_async(init_cachify_fixture: Any) -> None:
    """Test async pool with large max_size allows many concurrent accesses."""
    test_pool = pool(key='test-pool-large-async', max_size=10)
    concurrent_count = 0
    max_concurrent = 0

    @test_pool.pooled()
    async def concurrent_task(task_id: int) -> int:
        nonlocal concurrent_count, max_concurrent
        concurrent_count += 1
        max_concurrent = max(max_concurrent, concurrent_count)
        await asyncio.sleep(0.3)
        concurrent_count -= 1
        return task_id

    tasks = [asyncio.create_task(concurrent_task(i)) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert sorted(r for r in results if r is not None) == list(range(10))
    # With max_size=10, we should see significant concurrency
    # This is a timing-sensitive test, just ensure some concurrency happens
    assert max_concurrent >= 3  # At least some concurrency observed


def test_standalone_pooled_with_none_slot_exp(init_cachify_fixture: Any) -> None:
    """Test pooled() with slot_exp=None means no expiration."""
    cachify = init_cachify(default_pool_slot_expiration=600, is_global=False)

    @cachify.pooled(key='no-exp-pool', max_size=2, slot_exp=None)
    def process_task(task_id: int) -> int:
        sleep(0.1)
        return task_id

    # Should work normally without slot expiration
    result = process_task(1)
    assert result == 1


@pytest.mark.asyncio
async def test_standalone_pooled_async_with_none_slot_exp(init_cachify_fixture: Any) -> None:
    """Test async pooled() with slot_exp=None means no expiration."""
    cachify = init_cachify(default_pool_slot_expiration=600, is_global=False)

    @cachify.pooled(key='no-exp-pool-async', max_size=2, slot_exp=None)
    async def process_task(task_id: int) -> int:
        await asyncio.sleep(0.1)
        return task_id

    # Should work normally without slot expiration
    result = await process_task(1)
    assert result == 1
