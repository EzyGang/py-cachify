# Distributed Locks with Redis for Sync and Async Python (Mutex)

A lock, also known as a mutex, makes sure that a piece of code runs only once at a time.
It works like an electronic door lock that lets one person into a room, and it prevents data inconsistencies and race conditions.

`py-cachify` gives you this as a distributed lock. When you point it at Redis, the lock is shared by every process and every server
that uses the same Redis, so two workers of a web application cannot run the same job at the same moment.
The same `lock` works as a sync context manager, an async context manager and a decorator, so it fits an async FastAPI application as well as a script or a Celery task,
and you do not need separate sync and async versions.

Here is a lock around a slow job in an async function, with Redis as the backend:

```python
from py_cachify import init_cachify, lock
from redis.asyncio import from_url as async_from_url


# Use Redis, so that every process shares the same locks
init_cachify(async_client=async_from_url('redis://localhost:6379/0'))


# A second call with the same report_id waits for the first one to finish,
# for at most 5 seconds, and the lock frees itself after 10 seconds at the latest
@lock(key='report-{report_id}', nowait=False, timeout=5, exp=10)
async def build_report(report_id: int) -> None:
    ...
```

Decorate a FastAPI route handler or a background task in the same way. Calls with different `report_id` values do not block each other.
With the default `nowait=True`, a second call does not wait and raises `CachifyLockError` at once.

Without a Redis client, `py-cachify` uses an in-memory cache. That is fine for a single-process script and for trying the examples,
but every Python process then has its own locks, so it does not protect an application that runs several workers.

## py-cachify's locks

This tutorial shows how to use the locks, what parameters they have, and some common use cases.

Note: py-cachify's main focus is to provide a convenient way to use distributed locks, and not to replace the built-in ones.
Distributed locks matter most in web development, when scaling brings synchronisation problems and race conditions.

## What's next

We will dive deeper and look at some examples.
