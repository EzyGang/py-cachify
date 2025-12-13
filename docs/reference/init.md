# API Reference for ///init_cachify()///

## Overview

The `init_cachify` function initializes the `py-cachify` library, setting up the necessary synchronous and asynchronous
clients along with configuration options.

There are two main ways to use it:

- As a **global initializer** (the default), where you only care about the global decorators
  like `cached`, `lock`, and `once`, and you ignore the return value.
- As a **factory for dedicated instances**, where you call it with `is_global=False` to obtain a `Cachify` instance
  that you use directly via `instance.cached(...)`, `instance.lock(...)`, and `instance.once(...)`.

This function must be called at least once (with `is_global=True`) before using the global decorators.

If you are upgrading from 2.x, you may also want to review the [3.0.0 release notes](../release-notes.md#300) for a high-level summary of new configuration options (such as `default_cache_ttl`) and behavior changes that affect initialization.


## Function: ///init_cachify///

### Description

`init_cachify` configures the core caching and locking client used by py-cachify.

By default (`is_global=True`), it:

- Creates (or wires) the underlying clients.
- Registers them as the **global** client used by the top-level APIs:
  - `py_cachify.cached`
  - `py_cachify.lock`
  - `py_cachify.once`

Optionally (`is_global=False`), it:

- Creates an independent client that is *not* registered globally.
- Returns a `Cachify` instance that exposes instance-scoped decorators:
  - `Cachify.cached`
  - `Cachify.lock`
  - `Cachify.once`

### Signature

```python
from typing import Optional

from py_cachify import init_cachify
from py_cachify._backend._types._common import SyncClient, AsyncClient

def init_cachify(
    sync_client: Optional[SyncClient] = None,
    async_client: Optional[AsyncClient] = None,
    default_lock_expiration: Optional[int] = 30,
    default_cache_ttl: Optional[int] = None,
    prefix: str = 'PYC-',
    *,
    is_global: bool = True,
) -> Cachify:  # returns a Cachify instance
    ...
```

### Parameters

| Parameter                  | Type                  | Description                                                                                                                                                                                                                                                                              |
|---------------------------|-----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `sync_client`             | `Optional[SyncClient]`| The synchronous client used for caching operations. If `None`, a new in-memory client is created.                                                                                                                                                                                        |
| `async_client`            | `Optional[AsyncClient]`| The asynchronous client used for caching operations. If `None`, a new async client is created around an in-memory cache (see notes below for details).                                                                                                                                  |
| `default_lock_expiration` | `Optional[int]`       | Default expiration time (in seconds) for locks. Defaults to `30`.                                                                                                                                                                                                                       |
| `default_cache_ttl`       | `Optional[int]`       | Default TTL (in seconds) for cached values when a decorator omits `ttl`. `None` (the default) means values are stored without expiration when `ttl` is not explicitly specified.                                                                                                       |
| `prefix`                  | `str`                 | String prefix to prepend to all keys used in caching and locks. Defaults to `'PYC-'`.                                                                                                                                                                                                   |
| `is_global`               | `bool`                | Controls whether this call registers a **global** client. If `True` (default), the created client becomes the global backend used by the top-level `cached`, `lock`, and `once` decorators. If `False`, the global backend is not touched and only a dedicated `Cachify` instance is returned. |

### Returns

- `Cachify`: an instance object that exposes instance-scoped decorators:
  - `Cachify.cached(...)`
  - `Cachify.lock(...)`
  - `Cachify.once(...)`

#### When `is_global=True` (default)

- The returned `Cachify` instance and the top-level decorators (`cached`, `lock`, `once`) share the same underlying client.
- This is the traditional “initialize the library for my app” mode.
- Most users who only rely on global decorators do **not** need to keep or use the return value.

#### When `is_global=False`

- The global client is left untouched.
- The returned `Cachify` instance is fully independent and must be used explicitly:

  ```python
  instance = init_cachify(is_global=False)
  @instance.cached(key='my-key-{x}')
  def f(x: int) -> int:
      ...
  ```

- This is the mode to use when you want multiple, isolated caches/lockers in the same process (for example, different modules or subsystems using different backends or prefixes).

---

## Defaulting Behavior

The defaulting logic is designed so that:

- If **both** `sync_client` and `async_client` are `None`:
  - `sync_client` is set to a new in-memory cache.
  - `async_client` is set to a new async wrapper that uses that same in-memory cache under the hood.

- If `sync_client` is provided and is an in-memory cache implementation used by py-cachify:
  - And `async_client` is `None`:
    - `async_client` is set to a new async wrapper that reuses that same in-memory cache instance.

- If `sync_client` is provided and is **not** that in-memory cache implementation:
  - And `async_client` is `None`:
    - `async_client` is set to a new async wrapper over a fresh in-memory cache.

In practice:

- For typical **sync-only** or **async-only** applications, you will usually provide **one** client:
  - Either `sync_client=...` **or**
  - `async_client=...`
- If you need both sync and async usage to share the **same backend** (for example, Redis), pass both clients explicitly.

### Default cache TTL behavior

The `default_cache_ttl` parameter controls the **default TTL for cached values** used by both the global `@cached` decorator and instance-based `Cachify.cached`:

- If `default_cache_ttl` is an integer (for example, `60`):
  - Any `@cached(...)` or `Cachify.cached(...)` call that omits `ttl` will use that integer as the TTL.
- If `default_cache_ttl` is `None` (the default):
  - Any decorator that omits `ttl` will store values **without expiration** (behaving like `ttl=None` for the underlying client).
- If a decorator passes an explicit `ttl`:
  - `ttl=None` means “no expiration” regardless of `default_cache_ttl`.
  - `ttl=<int>` uses that integer and ignores `default_cache_ttl`.


---

## Usage Examples

### 1. Classic global initialization (most common)

For most applications you just configure a global backend once and only use the top-level decorators:

```python
from redis import from_url as redis_from_url
from redis.asyncio import from_url as async_redis_from_url

from py_cachify import cached, init_cachify, lock, once

# Global initialization (returns a Cachify instance, but we don't need it here)
init_cachify(
    sync_client=redis_from_url("redis://localhost:6379/0"),
    async_client=async_redis_from_url("redis://localhost:6379/1"),
    default_lock_expiration=60,
    default_cache_ttl=300,
    prefix='APP-',
)

@cached(key='sum-{a}-{b}', ttl=30)
def sum_two(a: int, b: int) -> int:
    return a + b

@lock(key='critical-{id}', nowait=False, timeout=10)
def critical_section(id: int) -> None:
    ...

@once(key='run-once-{id}', raise_on_locked=True)
def run_once(id: int) -> None:
    ...
```

In this mode:

- `cached`, `lock` and `once` all use the global client configured by `init_cachify()`.
- If you never call `init_cachify`, using those decorators will raise `CachifyInitError`.

### 2. Creating a dedicated instance without touching the global client

Sometimes you want a separate cache/locking backend for a particular subsystem or for testing. For that, you can create an independent instance:

```python
from py_cachify import init_cachify

# Global client, used by top-level decorators
init_cachify(
    # e.g. some Redis or other backend
    sync_client=...,
    async_client=...,
    prefix='GLOBAL-',
)

# Local instance: this does NOT modify the global client
local_cachify = init_cachify(
    sync_client=None,    # use in-memory sync cache
    async_client=None,   # in-memory async wrapper
    prefix='LOCAL-',
    is_global=False,
)

@local_cachify.cached(key='local-sum-{x}-{y}')
def local_sum(x: int, y: int) -> int:
    return x + y

@local_cachify.lock(key='local-lock-{name}')
def local_locked(name: str) -> None:
    ...

@local_cachify.once(key='local-once-{task_id}')
def local_once(task_id: str) -> None:
    ...
```

Here:

- The top-level decorators still use the global client (with prefix `GLOBAL-`).
- All `local_cachify.*` decorators use a completely independent client (with prefix `LOCAL-`).
- Caches and locks for the local instance will not interfere with global ones even if the keys look similar.

### 3. Multiple instances and isolation

You can create as many separate instances as you need, for example:

```python
from py_cachify import init_cachify

user_cache = init_cachify(prefix='USER-', is_global=False)
metrics_cache = init_cachify(prefix='METRICS-', is_global=False)

@user_cache.cached(key='user-{user_id}')
def get_user(user_id: int) -> dict:
    ...

@metrics_cache.cached(key='metric-{name}')
def compute_metric(name: str) -> float:
    ...
```

Even if the underlying clients are both in-memory, the prefixes and separation of clients ensure that:

- Entries written via `user_cache.cached` do not affect or collide with those written via `metrics_cache.cached`.
- You can swap backends independently (e.g. Redis for metrics, in-memory for users) by passing different `sync_client`/`async_client` to each `init_cachify(..., is_global=False)`.

---

## Custom Clients

The py-cachify library supports Redis (and Redis-compatible backends such as DragonflyDB, which use the same client APIs) for synchronous and asynchronous clients out of the box.
However, if you want to use other caching backends (such as Memcached, database-based, or file-based solutions),
you can create custom clients by complying with the `SyncClient` and `AsyncClient` protocols.

These custom implementations should match the following method signatures:

- For **synchronous clients (`SyncClient`)**:
  - `get(name: str) -> Optional[Any]`
  - `set(name: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> Any`
  - `delete(*names: str) -> Any`

- For **asynchronous clients (`AsyncClient`)**:
  - `get(name: str) -> Awaitable[Optional[Any]]`
  - `set(name: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> Awaitable[Any]`
  - `delete(*names: str) -> Awaitable[Any]`

### NX flag and locking semantics

The `nx` flag on `set` is crucial for the correctness of the locking APIs (`lock` and `once`):

- When `nx` is **False**:
  - `set(name, value, ex=..., nx=False)` should behave like a normal "upsert" operation: always set/overwrite the key.
  - The return value is backend-specific and not used by py-cachify in this mode.

- When `nx` is **True**:
  - `set(name, value, ex=..., nx=True)` must implement **set-if-not-exists** semantics atomically:
    - If the key does **not** exist (or is treated as expired), it should set the value and return a truthy value (e.g. `True`, `"OK"`, `b"OK"`).
    - If the key **already exists** (and is not expired), it should **not** modify the value and return a falsy value (e.g. `False`, `None`).
  - py-cachify relies on this behavior to implement `lock` / `once` as “acquire lock if free” via a single atomic operation.
  - In particular, we interpret the return value of `set(..., nx=True)` as a boolean indicating whether the lock has been acquired.

For Redis and Redis-compatible backends such as DragonflyDB, this usually maps directly to:

```python
redis_client.set(name, value, ex=ex, nx=nx)
```

which internally uses the `SET key value NX EX ttl` command and returns a truthy value when the key was set and `None` when it was not.

For custom backends:

- To have **correct distributed locking semantics**, you must implement `set(..., nx=True)` as an atomic "set-if-absent" operation and return a truthy/falsy value as described above.
- If your backend cannot provide atomic `nx=True` behavior, `lock` and `once` will only offer best-effort mutual exclusion and may admit concurrent entries under rare races.

By adhering to these protocols (including the `nx` semantics), you can integrate your custom backend while maintaining compatibility with py-cachify's caching and locking mechanisms.

### Example Custom Client Integration

```python
from typing import Any, Optional, Awaitable

class CustomSyncClient:
    def get(self, name: str) -> Optional[Any]:
        # Implementation for getting a value from the cache
        ...

    def set(self, name: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> Any:
        # Implementation for setting a value in the cache.
        # When nx=True, this MUST act as an atomic "set-if-not-exists" and
        # return a truthy value on success and a falsy value on failure.
        ...

    def delete(self, *names: str) -> Any:
        # Implementation for deleting keys from the cache
        ...

class CustomAsyncClient:
    async def get(self, name: str) -> Optional[Any]:
        # Implementation for asynchronously getting a value from the cache
        ...

    async def set(self, name: str, value: Any, ex: Optional[int] = None, nx: bool = False) -> Awaitable[Any]:
        # Implementation for asynchronously setting a value in the cache.
        # When nx=True, this MUST act as an atomic "set-if-not-exists" and
        # return a truthy value on success and a falsy value on failure.
        ...

    async def delete(self, *names: str) -> Awaitable[Any]:
        # Implementation for asynchronously deleting keys from the cache
        ...

# Initialize a global Cachify client with custom clients
init_cachify(
    sync_client=CustomSyncClient(),
    async_client=CustomAsyncClient(),
)

# Or create a dedicated instance without touching global state
custom_cachify = init_cachify(
    sync_client=CustomSyncClient(),
    async_client=CustomAsyncClient(),
    is_global=False,
)
```

This flexibility allows you to utilize a caching backend of your choice while leveraging the py-cachify library's capabilities effectively, including robust `lock` / `once` behavior when `nx` is implemented atomically. 

---

## Notes

- It is crucial to call `init_cachify` with `is_global=True` at least once before performing any global caching or locking operations with `cached`, `lock`, or `once`. Failing to do so will result in a `CachifyInitError` when attempting to access global caching features.
- `Cachify` instances created with `is_global=False` do *not* depend on the global initialization and can be used independently.
- The `sync_client` and `async_client` parameters should comply with the `SyncClient` and `AsyncClient` protocols, respectively.