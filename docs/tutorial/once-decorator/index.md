# Once: run a Celery or Taskiq task only once at a time

## Description

The `@once` decorator makes sure a function runs only once at a time for a given key. A second call with the same key, made while the first is still running, returns right away without running the function. It works for sync and async functions, so it fits the tasks of `celery`, `taskiq`, `darq` and `dramatiq`.

It's built on the same distributed lock as `lock`. So with Redis behind it, the guard holds across all your worker processes. With the default in-memory cache, every process has its own memory and the guard only holds inside one process. Set up Redis as shown in [initialization](../initial-setup/initialization.md) before you rely on it in a real deployment.

## Prevent a Celery task from running twice at the same time

Say there's a spawner task that submits one small task per order to check its status:

```python
from uuid import UUID

from celery import shared_task


# This is scheduled to run every 5 minutes
@shared_task()
def check_in_progress_orders() -> None:
    orders = ...  # hit the database and get all orders
    [check_order.s(order_id=order.id).delay() for order in orders]


# This is spawned by the previous one
@shared_task()
def check_order(order_id: UUID) -> None:
    # check the order progress, update state, save
    ...
```

The result of each task doesn't matter here, but running it twice for the same `order_id` at the same time could break things. A check that takes longer than five minutes would do exactly that.

Put `@once` under `@shared_task()` and give it a key with the argument in it:

```python
from uuid import UUID

from celery import shared_task
from py_cachify import once


@shared_task()
@once(key='check_order-{order_id}')
def check_order(order_id: UUID) -> None:
    # check the order progress, update state, save
    ...
```

While one `check_order` runs for an `order_id`, every other call for the same `order_id` exits early and returns `None`. Calls for other orders aren't affected. The skipped task counts as a successful one in Celery, because the function simply returned.

## Prevent a Taskiq task from running twice at the same time

Taskiq tasks are async functions, and the order is the same: the broker's decorator on the outside, `@once` underneath.

```python
from taskiq import InMemoryBroker  # use your real broker here
from py_cachify import once

broker = InMemoryBroker()


@broker.task
@once(key='check_order-{order_id}')
async def check_order(order_id: int) -> None:
    # check the order progress, update state, save
    ...
```

## What to do with a skipped call

By default a skipped call returns `None`. Two parameters change that:

- `return_on_locked='skipped'` returns that value instead of `None`, so the caller can tell a skipped run from a finished one.
- `raise_on_locked=True` raises `CachifyLockError` instead. In Celery you can catch it and retry the task later.

```python
@shared_task()
@once(key='check_order-{order_id}', raise_on_locked=False, return_on_locked=None)  # these are the defaults
def check_order(order_id: UUID) -> None:
    ...
```

## How long the guard lasts

The guard is released when the function returns, and also when it raises, so a failed task can be retried at once.

If the worker dies in the middle of a task, nothing releases it. The key expires on its own after `default_lock_expiration`, which is 30 seconds unless you change it in `init_cachify`. The same 30 seconds apply to a task that runs longer than that: after 30 seconds a second call is let in while the first is still working. For tasks that run for minutes, raise the value:

```python
init_cachify(
    sync_client=from_url(redis_url),
    default_lock_expiration=15 * 60,  # the longest a task may run, in seconds
)
```

The guard of a stuck task can also be cleared by hand with `check_order.release(order_id=...)`.

## What's next

You can always check the [full reference for once](../../reference/once.md).

## Conclusion

This concludes the tutorial for py-cachify.

It covered the basics of the package and glanced over common cases.
Caching and locking are pretty common topics, yet they are always unique to the specifics of the app and tasks that the programmer wants to solve.

Py-Cachify tries to help you cover your specific cases by giving you lock- and once-based tools built on the same underlying mechanism, so you can adapt them to your needs without bloating your codebase.

See the [full API reference for init_cachify](../../reference/init.md).
