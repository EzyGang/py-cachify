# API Reference for ///@cached()/// Decorator

## Overview

The `cached` decorator provides a caching mechanism that stores the result of a function based on a specified key, time-to-live (TTL), and optional encoding/decoding functions. It can be applied to both synchronous and asynchronous functions, facilitating quick access to previously computed results. This includes respecting a configurable `default_cache_ttl` when no explicit `ttl` is provided.

---

## Function: ///cached///

### Description

The `cached` decorator caches the results of a function execution using a unique key. If the function is called again with the same key before the TTL expires, the cached result is returned instead of re-executing the function. This is particularly useful for expensive computations or IO-bound tasks.

There are two main ways to use caching with py-cachify:

- Via the **global** `cached` decorator exported from `py_cachify`, which relies on a globally initialized client.
- Via **instance-based** decorators obtained from a `Cachify` object created by `init_cachify(is_global=False)`.

### Parameters

| Parameter            | Type                            | Description                                                                                                   |
|---------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------|
| `key`               | `str`                           | The key used to identify the cached result, which can utilize formatted strings to create dynamic keys. (i.e. `key='my_key-{func_arg}'`)       |
| `ttl`               | `Union[int, None]`, optional    | Time-to-live (seconds) for the cached result. If omitted, the decorator uses the cache client's `default_cache_ttl` (configured via `init_cachify`). If `ttl` is `None`, the value is stored without expiration. If `ttl` is an integer, that value is used directly and overrides any `default_cache_ttl`.   |
| `enc_dec`           | `Union[Tuple[Encoder, Decoder], None]`, optional  | A tuple containing the encoding and decoding functions for the cached value. Defaults to `None`, which means that no encoding or decoding functions will be applied. |
| `stampede_protect`  | `Union[StampedeProtect, LockConf]`, optional | What happens when several callers miss the same key at once. `StampedeProtect.OFF`: every caller runs the function. `StampedeProtect.IN_MEMORY` (default): callers in one process wait for the run already in progress. `StampedeProtect.LOCK` or `LockConf(...)`: additionally one process computes while the others wait for it. See [Cache stampedes](#cache-stampedes). |

`LockConf` fields, each defaulting to the value configured in `init_cachify`:

| Field           | Type                 | Description |
|-----------------|----------------------|-------------|
| `exp`           | `Union[int, None]`   | Lock expiration in seconds. Defaults to `default_lock_expiration` (30). |
| `wait`          | `Union[float, None]` | Seconds to wait for another process's value before computing it without the lock. Defaults to `exp`; `None` waits as long as the lock exists. |
| `poll_interval` | `float`              | Seconds between two checks while waiting. Defaults to `lock_poll_interval` (0.1). |


### Default TTL behavior

The effective TTL for a cached value is determined as follows (higher items take precedence over lower ones):

1. If you pass an explicit integer, for example `@cached(..., ttl=30)`, that TTL is used and overrides any `default_cache_ttl`.
2. If you pass `ttl=None`, the cache entry is stored **without expiration** (infinite TTL in most backends), even if `default_cache_ttl` is configured.
3. If you omit `ttl` entirely, the decorator will fall back to the underlying client's `default_cache_ttl`:
   - `default_cache_ttl` is configured via `init_cachify(default_cache_ttl=...)` for both global and instance-based usage.
   - If `default_cache_ttl` is `None` (the default), omitting `ttl` behaves like “no expiration”.

This lets you define a global or instance-specific default TTL once and only override it where needed. When you do not configure `default_cache_ttl` at all (leaving it as `None`) and also omit `ttl` on the decorator, the behavior is the same as in previous versions of py-cachify: cached values are stored without expiration by default.

### Returns

- `WrappedFunctionReset`: A wrapped function (either synchronous or asynchronous) with an additional `reset` method attached for cache management. The `reset(*args, **kwargs)` method allows the user to manually reset the cache for the function using the same key.

### Method Behavior

1. **For Synchronous Functions**:
    - Checks if a cached value exists for the provided key.
    - If the cached value exists, it returns the decoded value.
    - If not, it executes the function, caches the result (after encoding, if specified), and then returns the result.
    - With `StampedeProtect.IN_MEMORY` (the default), threads that miss the same key while the function is running wait for that run instead of starting their own.
    - With `StampedeProtect.LOCK` or a `LockConf`, the run takes a lock in the cache backend first, as described in [Cache stampedes](#cache-stampedes).

2. **For Asynchronous Functions**:
    - Similar checks are performed in an asynchronous context using `await`.
    - The caching behavior mirrors the synchronous version: tasks that miss the same key while the function is running await that run.


### Global Usage Example

```python
from py_cachify import cached, init_cachify


# Configure a default cache TTL of 60 seconds for all cached values
init_cachify(default_cache_ttl=60)


@cached('my_cache_key')
def compute_expensive_operation(param: int) -> int:
    # Uses default_cache_ttl=60 as TTL
    return param * 2


@cached('my_async_cache_key-{param}', ttl=30)
async def fetch_data(param: int) -> dict:
    # Overrides the default and uses ttl=30
    return {'data': param}
```

### Instance-based Usage

If you need multiple independent caches (for example, per module or subsystem), you can create dedicated `Cachify` instances via `init_cachify(is_global=False)` and use their `cached` method instead of the global decorator.

```python
from py_cachify import init_cachify

# Create a dedicated instance that does not affect the global client
# and set a default TTL of 300 seconds for this instance
local_cachify = init_cachify(is_global=False, prefix='LOCAL-', default_cache_ttl=300)
@local_cachify.cached(key='local-{x}-{y}')
def local_sum(x: int, y: int) -> int:
    # Uses the instance-level default_cache_ttl=300
    return x + y
```

- `@cached(...)` (global) uses the client configured by a global `init_cachify()` call.
- `@local_cachify.cached(...)` uses a client that is completely independent from the global one.

### Multi-layer Usage

It is possible to layer caches by stacking `cached` decorators (for example, a global cache inside a local instance cache).

```python
from py_cachify import cached, init_cachify

# Global initialization
init_cachify()

# Local instance with a shorter TTL that wraps the global one
local = init_cachify(is_global=False, prefix='LOCAL-')

@local.cached(key='local-expensive-{x}', ttl=5)
@cached(key='expensive-{x}', ttl=60)
def expensive(x: int) -> int:
    return x * 10
```

In this scenario:

- The **outer** cache (local instance) provides a short-lived layer over the **inner** global cache.
  - Could be useful to add in-memory cache over a Redis/Dragonfly cache, to further speed up execution (useful for hard to refactor N+1 processing, for example).
- Calling `expensive.reset(x)` will:
  - Clear the local cache entry for that call.
  - Attempt to call `reset` on the inner cached layer as well, if present, so both layers are cleared for that key.

This makes multi-layer setups behave intuitively when resetting cached values.

### Cache stampedes

A stampede is many callers asking for the same key at the moment it isn't cached: after a deploy, after the value expired, for a new item. Without protection, every one of them misses and runs the function, so 100 concurrent requests for a cold key call a slow database query or API 100 times at once.

`cached` has two layers against it, chosen with `stampede_protect`.

**In one process (`StampedeProtect.IN_MEMORY`, the default).** The first caller that misses runs the function; callers that miss the same key while it runs wait for its result instead of running it again. In async code the function runs as a separate task, so a caller that is cancelled (a client that disconnects) cancels neither the computation nor the other callers, and the value is still cached. If the function raises, every caller of that round gets the same exception, nothing is cached, and the next caller tries again. Cache hits don't go through this layer at all.

Callers that shared one run receive the same object, not separate copies, so a caller that mutates the result changes it for the others.

With several processes (uvicorn or gunicorn workers, several servers), each process still runs the function once.

**Across processes (`StampedeProtect.LOCK` or `LockConf(...)`).** The one caller per process that the first layer lets through then:

1. Reads the cache again and returns the value if another process has filled it.
2. Tries to take a lock key in the backend (`SET NX` with `exp`). The lock key is the cache key with `_lock` appended, for example `PYC-user-42-cached_lock`, a name no other py-cachify key can have.
3. If it got the lock, it reads the cache once more, runs the function only if the value is still missing, stores it, and releases the lock.
4. If it didn't get the lock, it waits: every `poll_interval` it reads the cache and returns the value as soon as it is there. Only when the value is still missing does it try to take the lock itself. A waiter never has to take the lock to read a value that already exists.
5. If nothing has arrived after `wait` seconds, it runs the function without the lock and stores the result. Waiting never raises an error.

So a burst at a cold key runs the function once across all processes, and the waiters get the value within one poll interval after it is stored.

Things to know:

- **Poll interval.** Each waiting process sends a `GET` and a `SET NX` to the backend every `poll_interval`. Thanks to the first layer that's one waiter per process, not one per request, but a very short interval on many processes still adds load to Redis. The default 0.1 s adds at most 0.1 s of latency for waiters.
- **A computation that outlives the lock.** If the function takes longer than `exp`, the lock expires and another process may run the function too. Both results are stored and the later one wins. Set `exp` above the slowest expected run.
- **A process that dies while holding the lock** leaves it in place until `exp` passes; then the next caller takes it and computes.
- **Releasing.** The holder deletes the lock only if it still holds its own token. The client protocol has no atomic compare-and-delete, so this is a read followed by a delete; in the rare case that the lock expires and another process takes it between the two, that process's lock is deleted early, which at worst allows one more computation.
- **`None` results are never cached** (as before), so with the lock, callers of a function that returns `None` take the lock one after another.

```python
from py_cachify import LockConf, StampedeProtect, cached


# Sync: one process computes, the others wait up to 10 seconds for the value.
@cached(key='report-{day}', ttl=300, stampede_protect=LockConf(exp=60, wait=10))
def build_report(day: str) -> dict:
    ...


# Async: lock settings from init_cachify.
@cached(key='user-{user_id}', ttl=300, stampede_protect=StampedeProtect.LOCK)
async def get_user(user_id: int) -> dict:
    ...


# No protection: every concurrent caller that misses runs the function.
@cached(key='token-{user_id}', stampede_protect=StampedeProtect.OFF)
async def issue_token(user_id: int) -> str:
    ...
```

Stacking `lock` or `once` around `cached` is not a stampede guard: with `lock`, every waiter has to take the lock before it can even read the cache, so waiters pass one at a time and the last ones run into the lock's timeout; `once` answers concurrent callers with `return_on_locked` even when the value is already cached.

### Resetting the Cache

You can reset the cache for either a synchronous or asynchronous function by calling the `reset` method attached to the wrapped function.

```python
# Reset cache for a synchronous function
compute_expensive_operation.reset()

# Reset cache for an asynchronous function
await fetch_data.reset(param='param-value')
```

For instance-based usage, the pattern is the same:

```python
local_sum.reset(x=1, y=2)
```

Calling `reset` while a computation for that key is running doesn't strand the callers waiting for it: they receive that computation's result. As before, that result is stored when the computation ends, even if the reset came in between.

### Notes

- Ensure that both the serialization and deserialization functions defined in `enc_dec` are efficient to preserve optimal performance.
- If py-cachify is not initialized through `init_cachify` with `is_global=True`, using the global `@cached` decorator will raise a `CachifyInitError` at runtime.
- `Cachify` instances created with `is_global=False` do not depend on global initialization and can be used independently.

### Type Hints Remark

Currently, Python's type hints have limitations in fully capturing a function's original signature when transitioning to a protocol-based callable in a decorator, particularly for methods (i.e., those that include `self`). `ParamSpec` can effectively handle argument and keyword types for functions but doesn't translate well to methods within protocols like `WrappedFunctionReset`. I'm staying updated on this issue and recommend checking the following resources for more insights into ongoing discussions and proposed solutions:

- [Typeshed Pull Request #11662](https://github.com/python/typeshed/pull/11662)
- [Mypy Pull Request #17123](https://github.com/python/mypy/pull/17123)
- [Python Discussion on Allowing Self-Binding for Generic ParamSpec](https://discuss.python.org/t/allow-self-binding-for-generic-paramspec/50948)

Once any developments occur, I will quickly update the source code to incorporate the changes.
