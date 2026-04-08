# Pool - Methods in Py-Cachify

## The ///size()/// Method

The `size()` method returns the current number of occupied slots in the pool. Use it to monitor pool utilization or make decisions before attempting to acquire.

### Asynchronous Usage

```python
import asyncio

from py_cachify import init_cachify, pool


init_cachify()


async def main() -> None:
    worker_pool = pool(key='monitor-pool', max_size=3)

    print(f'Pool size before: {await worker_pool.asize()}')

    async with worker_pool:
        print(f'Pool size during: {await worker_pool.asize()}')

    print(f'Pool size after: {await worker_pool.asize()}')


if __name__ == '__main__':
    asyncio.run(main())
```

<!-- termynal -->
```bash
$ python main.py

# The output
Pool size before: 0
Pool size during: 1
Pool size after: 0
```

### Synchronous Usage

```python
from py_cachify import init_cachify, pool


init_cachify()


worker_pool = pool(key='sync-monitor', max_size=5)

print(f'Pool size: {worker_pool.size()}')

with worker_pool:
    print(f'Pool size during: {worker_pool.size()}')
```

## Method Reference

| Method | Context | Returns |
|--------|---------|---------|
| `size()` | Synchronous | `int`: current occupied slot count |
| `asize()` | Asynchronous | `int`: current occupied slot count |

Both methods return the count after cleaning up expired slots, so the number reflects actual available capacity.

## Practical Example: Load Shedding

Use `size()` to implement load shedding - rejecting work when the pool is near capacity:

```python
import asyncio

from py_cachify import init_cachify, pool


init_cachify()


async def process_with_backpressure(task_id: str, worker_pool) -> None:
    current_size = await worker_pool.asize()
    max_size = worker_pool._max_size  # Accessing internal attribute for threshold

    # Reject if pool is 80% full
    if current_size >= max_size * 0.8:
        print(f'Task {task_id}: Server busy, try again later')
        return

    async with worker_pool:
        print(f'Task {task_id}: Processing')
        await asyncio.sleep(0.5)


async def main() -> None:
    worker_pool = pool(key='backpressure-pool', max_size=10)

    # Simulate many incoming tasks
    tasks = [process_with_backpressure(f'task-{i}', worker_pool) for i in range(15)]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
```

## What's Next

We will see how to use pools as decorators with the `@pooled()` decorator and handle full pool scenarios with callbacks.
