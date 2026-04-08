# API Reference for ///pool()/// and ///@pooled()///

## Overview

The `pool()` class and `@pooled()` decorator manage concurrent execution slots with a configurable maximum capacity. Unlike locks which enforce mutual exclusion (one at a time), pools enforce capacity limits (N at a time).

There are two main ways to use pools with py-cachify:

- Via the **global** `pool()` class and `@pooled()` decorator exported from `py_cachify`, which rely on a globally initialized client.
- Via **instance-based** pools obtained from a `Cachify` object created by `init_cachify(is_global=False)`.

## Class: ///pool()///

### Description

The `pool()` class manages a distributed pool of execution slots using your cache backend. It supports both synchronous and asynchronous contexts via context manager protocols (`__enter__` / `__exit__` and `__aenter__` / `__aexit__`).

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | The key used to identify this pool in the cache. Must be unique per pool. |
| `max_size` | `int` | Maximum number of concurrent slots allowed in this pool. |
| `slot_exp` | `Union[int, None, UnsetType]`, optional | TTL for individual pool slots in seconds. Defaults to `UNSET`, which uses `default_pool_slot_expiration` from `init_cachify()`. Use `None` for no expiration. |

### Context Manager Usage

**Asynchronous:**

```python
async with pool(key='worker-pool', max_size=10):
    # Up to 10 concurrent executions across all processes
    await do_work()
```

**Synchronous:**

```python
with pool(key='worker-pool', max_size=10):
    # Synchronous work within pool capacity
    do_work()
```

### Methods

| Method | Context | Returns | Description |
|--------|---------|---------|-------------|
| `size()` | Synchronous | `int` | Returns the current number of occupied slots after cleaning expired entries. |
| `asize()` | Asynchronous | `int` | Returns the current number of occupied slots after cleaning expired entries. |
| `pooled(on_full, raise_on_full)` | Both | `WrappedFunctionPool` | Creates a decorator factory bound to this pool instance. See below. |

### Instance Method: ///pooled()///

Use a pool instance as a decorator factory instead of the standalone `@pooled()` decorator:

```python
from py_cachify import init_cachify, pool


init_cachify()


# Create pool instance
worker_pool = pool(key='worker', max_size=5)


# Use instance method as decorator
@worker_pool.pooled(on_full=handle_full)
async def process_task(data: str) -> str:
    return f'processed-{data}'
```

The instance method shares the same parameters as the standalone `@pooled()` decorator but reuses the pool instance instead of creating one per decorated function.

## Decorator: ///@pooled()///

### Description

The `@pooled()` decorator wraps functions with automatic pool slot acquisition. When the pool is full, behavior is controlled by `raise_on_full` and `on_full` parameters.

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Pool key supporting format strings with function arguments (e.g., `'pool-{user_id}'`). Each unique resolved key creates a separate pool instance. |
| `max_size` | `int` | Maximum concurrent slots for this pool. |
| `on_full` | `Callable[..., Any]`, optional | Callback invoked when pool is full. Receives the exact `*args, **kwargs` passed to the wrapped function. Return value becomes the decorator's return value. Defaults to `None` (returns `None` when full). |
| `raise_on_full` | `bool`, optional | If `True`, raise `CachifyPoolFullError` when pool is full instead of calling `on_full`. Defaults to `False`. |
| `slot_exp` | `Union[int, None, UnsetType]`, optional | TTL for pool slots in seconds. Defaults to `UNSET`, using `default_pool_slot_expiration` from `init_cachify()`. |

### Returns

- `WrappedFunctionPool`: A wrapped function (sync or async) with an additional `size(*args, **kwargs)` method for checking pool occupancy.

### Attached Method: ///size()///

Decorated functions have a `size()` method attached:

```python
from py_cachify import init_cachify, pooled


init_cachify()


@pooled(key='api-pool-{user_id}', max_size=5)
async def call_api(user_id: str) -> dict:
    return {'user_id': user_id}


async def main():
    # Check occupancy for user_id='123'
    occupancy = await call_api.size(user_id='123')
    print(f'Pool occupancy: {occupancy}')
```

The `size()` method uses the same key formatting as the decorator, checking the specific pool instance that would be used for those arguments.

## Error Handling

- `CachifyPoolFullError`: Raised when attempting to acquire a slot from a full pool with `raise_on_full=True`, or when using the `pool()` context manager directly (which always raises on full).

- `CachifyInitError`: Raised if py-cachify is not initialized via `init_cachify()` with `is_global=True` before using global `pool()` or `@pooled()`.

## Slot Expiration Behavior

Slots automatically expire after `slot_exp` seconds. Important characteristics:

1. Expiration cleans up the slot count but does not interrupt running code
2. A process holding a slot that expires continues executing; the slot simply becomes available for counting purposes
3. On next acquire attempt, expired slots are cleaned up and the count reflects actual capacity
4. Default `slot_exp` comes from `default_pool_slot_expiration` in `init_cachify()` (600 seconds / 10 minutes if not configured)

## Instance-Based Usage

Create dedicated pool instances via `init_cachify(is_global=False)`:

```python
from py_cachify import init_cachify


# Global initialization
init_cachify()


# Local instance with independent pools
local_cachify = init_cachify(is_global=False, prefix='LOCAL-')


# Instance-based pool
local_pool = local_cachify.pool(key='local-worker', max_size=3)


async with local_pool:
    # Uses local instance, not global
    pass


# Instance-based decorator
@local_cachify.pooled(key='local-task', max_size=2)
async def local_task():
    pass
```

Global `pool()` and `@pooled()` use the client from `init_cachify(is_global=True)`. Instance-based pools use their own client with separate prefix and configuration.

## Usage Examples

### Context Manager with Error Handling

```python
import asyncio

from py_cachify import init_cachify, pool, CachifyPoolFullError


init_cachify()


async def attempt_work(worker_pool) -> None:
    try:
        async with worker_pool:
            print('Acquired slot and working')
            await asyncio.sleep(1)
    except CachifyPoolFullError:
        print('Pool full - skipping work')


async def main():
    worker_pool = pool(key='work-pool', max_size=2)

    # Try to run 4 workers in a pool of 2
    await asyncio.gather(*[attempt_work(worker_pool) for _ in range(4)])


if __name__ == '__main__':
    asyncio.run(main())
```

### Decorator with Callback

```python
from py_cachify import init_cachify, pooled


init_cachify()


def reschedule(*args, **kwargs):
    # Callback receives same args/kwargs as original function
    task_id = kwargs.get('task_id')
    print(f'Rescheduling task {task_id}')
    return {'rescheduled': True, 'task_id': task_id}


@pooled(key='task-pool', max_size=3, on_full=reschedule)
async def process_task(task_id: str) -> dict:
    return {'completed': True, 'task_id': task_id}
```

### Dynamic Keys (Per-User Pools)

```python
from py_cachify import init_cachify, pooled


init_cachify()


@pooled(key='user-limit-{user_id}', max_size=5, raise_on_full=True)
async def user_operation(user_id: str, data: str) -> dict:
    # Each user_id gets their own pool of size 5
    return {'user_id': user_id, 'processed': data}


async def main():
    # Different pools: 'user-limit-1' and 'user-limit-2'
    await user_operation(user_id='1', data='a')
    await user_operation(user_id='2', data='b')
```

## Type Hints Remark

Currently, Python's type hints have limitations in fully capturing a function's original signature when transitioning to a protocol-based callable in a decorator, particularly for methods (those that include `self`). `ParamSpec` can effectively handle argument and keyword types for functions but does not translate well to methods within protocols like `WrappedFunctionPool`. We are staying updated on this issue and recommend checking the following resources for more insights:

- [Typeshed Pull Request #11662](https://github.com/python/typeshed/pull/11662)
- [Mypy Pull Request #17123](https://github.com/python/mypy/pull/17123)
- [Python Discussion on Allowing Self-Binding for Generic ParamSpec](https://discuss.python.org/t/allow-self-binding-for-generic-paramspec/50948)

Once any developments occur, we will update the source code to incorporate the changes.

## Backend Requirements

Pools require the same backend semantics as locks: an atomic "set-if-not-exists" operation via the `nx` flag. The correctness of pool slot acquisition depends on this atomic behavior. Built-in clients (in-memory, Redis examples) implement this correctly. Custom clients must follow the same `nx` contract as documented in the initialization reference.
