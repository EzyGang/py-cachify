# Pool - Using ///@pooled()/// Decorator

## Decorator Overview

The `@pooled()` decorator wraps functions with automatic pool acquisition. When the pool is full, you can either raise an error or invoke a callback with the original function arguments.

## Basic Decorator Usage

```python
import asyncio

from py_cachify import init_cachify, pooled, CachifyPoolFullError


init_cachify()


@pooled(key='api-call-pool', max_size=3, raise_on_full=True)
async def call_external_api(user_id: str) -> dict:
    # Simulate API call
    await asyncio.sleep(1)
    return {'user_id': user_id, 'data': 'response'}


async def main() -> None:
    # This works - within pool limit
    result = await call_external_api('user-1')
    print(f'Result: {result}')


if __name__ == '__main__':
    asyncio.run(main())
```

## The ///on_full/// Callback

When `raise_on_full=False` (the default), you can provide an `on_full` callback. This receives the exact same `*args, **kwargs` as the original function call.

This flexibility enables various fallback strategies:

### Example 1: Rescheduling (Celery/Taskiq)

```python
from py_cachify import init_cachify, pooled
from celery import shared_task


init_cachify()


def reschedule_task(*args, **kwargs):
    # Reschedule this task to run later
    process_user_task.delay(*args, **kwargs)
    return {'status': 'rescheduled', 'user_id': kwargs.get('user_id')}


@shared_task()
@pooled(key='user-processing-pool-{user_id}', max_size=2, on_full=reschedule_task)
def process_user_task(user_id: str) -> dict:
    # Process user data
    return {'status': 'completed', 'user_id': user_id}
```

### Example 2: Returning Cached Data

```python
import asyncio

from py_cachify import init_cachify, pooled, cached


init_cachify()


# Fallback returns stale cached data
def return_cached(*args, **kwargs):
    user_id = kwargs.get('user_id')
    # Return a sensible default or fetch from cache
    return {'user_id': user_id, 'data': 'stale-cache', 'fresh': False}


@pooled(key='expensive-query-pool', max_size=5, on_full=return_cached)
@cached(key='expensive-query-{user_id}', ttl=60)
async def expensive_query(user_id: str) -> dict:
    await asyncio.sleep(2)  # Simulate slow query
    return {'user_id': user_id, 'data': 'fresh-data', 'fresh': True}


async def main() -> None:
    result = await expensive_query(user_id='123')
    print(f'Result: {result}')


if __name__ == '__main__':
    asyncio.run(main())
```

### Example 3: Logging and Dropping

```python
import asyncio
import logging

from py_cachify import init_cachify, pooled


init_cachify()
logger = logging.getLogger(__name__)


def log_and_skip(*args, **kwargs):
    user_id = kwargs.get('user_id', 'unknown')
    logger.warning(f'Pool full - dropping task for user {user_id}')
    return None


@pooled(key='notification-pool', max_size=10, on_full=log_and_skip)
async def send_notification(user_id: str, message: str) -> dict:
    await asyncio.sleep(0.5)
    return {'sent': True, 'user_id': user_id}
```

## Dynamic Keys with Format Strings

Like `@cached()` and `@lock()`, `@pooled()` supports dynamic keys:

```python
from py_cachify import init_cachify, pooled


init_cachify()


@pooled(key='user-pool-{user_id}', max_size=2, on_full=lambda **kw: None)
async def process_user(user_id: str) -> dict:
    return {'user_id': user_id}


# Each user_id gets its own pool of size 2
async def main() -> None:
    # These use different pools (user-pool-1, user-pool-2)
    await process_user(user_id='1')
    await process_user(user_id='2')
```

## Checking Pool Size on Decorated Functions

The `@pooled()` decorator attaches a `size()` method to the wrapped function:

```python
import asyncio

from py_cachify import init_cachify, pooled


init_cachify()


@pooled(key='checkable-pool-{user_id}', max_size=3)
async def do_work(user_id: str) -> str:
    await asyncio.sleep(1)
    return f'work-done-{user_id}'


async def main() -> None:
    # Check pool occupancy for user_id='123'
    occupancy = await do_work.size(user_id='123')
    print(f'Pool occupancy for user 123: {occupancy}')


if __name__ == '__main__':
    asyncio.run(main())
```

The `size(*args, **kwargs)` method uses the same key formatting as the decorator, so you check the specific pool instance that would be used for those arguments.

## Synchronous Usage

`@pooled()` works with synchronous functions too:

```python
from py_cachify import init_cachify, pooled


init_cachify()


@pooled(key='sync-pool', max_size=2, raise_on_full=True)
def sync_work(task_id: str) -> str:
    return f'completed-{task_id}'


# Usage
def main():
    try:
        result = sync_work('task-1')
        print(f'Result: {result}')
    except Exception as e:
        print(f'Failed: {e}')


if __name__ == '__main__':
    main()
```

## Conclusion

The `@pooled()` decorator integrates pool management into your function definitions. The `on_full` callback receives the same arguments as your function, enabling flexible responses: rescheduling, returning cached data, logging, or any custom logic your application requires.

## What's Next

The full API reference for `pool()` and `@pooled()` is available [here](../../reference/pool.md).
