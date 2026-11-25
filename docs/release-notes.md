# Release Notes

## [3.3.0](https://github.com/EzyGang/py-cachify/releases/tag/v3.3.0)

### Features & Enhancements

#### **Stampede protection in `cached`**:
  - **Concurrent misses in one process are now collapsed by default.** When several callers (threads or tasks) miss the same key while the function is running, they wait for that run instead of calling the function again. If it raises, they all get the same exception and nothing is cached. Callers that share a run get the same result object. Turn it off per decorator with `@cached(..., stampede_protect=StampedeProtect.OFF)`.
  - New `stampede_protect=StampedeProtect.LOCK` makes one process compute a missing value while the other processes wait for it, through a lock key in the cache backend. Waiters read the cache on every poll and return as soon as the value is there; after the wait limit they compute it themselves instead of raising.
  - `LockConf(exp=..., wait=..., poll_interval=...)` sets the lock per decorator; unset fields fall back to `init_cachify` (`default_lock_expiration`, `lock_poll_interval`, and `wait` defaults to `exp`).
  - New exports: `StampedeProtect`, `LockConf`. The option exists on `Cachify.cached` too. Cache hits, `lock`, `once`, pools and the client protocol are unchanged.
  - See [Cache stampedes](reference/cached.md#cache-stampedes) in the `cached` reference.

---

## [3.2.0](https://github.com/EzyGang/py-cachify/releases/tag/v3.2.0)

### Breaking Changes

#### **Python 3.9 support dropped**:
  - The supported Python versions are now 3.10–3.14.
  - Python 3.9 reached end-of-life in October 2025; it is removed from `requires-python`, classifiers and the test matrix.
  - Projects still on 3.9 will keep resolving to py-cachify 3.1.x.

---

## [3.1.0](https://github.com/EzyGang/py-cachify/releases/tag/v3.1.0)

### Features & Enhancements

#### **Resource Pools**:
  - New `pool()` class for managing concurrent execution slots with `max_size` limit.
  - Use as context manager: `async with pool(key='worker-pool', max_size=10)`
  - Use as decorator via `@pooled(key='...', max_size=N, on_full=callback)`
  - `on_full` callback receives same `*args, **kwargs` as wrapped function, enabling rescheduling, logging, or fallback logic.
  - `raise_on_full=True` option to raise `CachifyPoolFullError` instead of calling on_full.
  - `slot_exp` parameter for slot TTL (defaults to `default_pool_slot_expiration` from `init_cachify()`, default 600 seconds).
  - `size()` and `asize()` methods to check current pool occupancy.
  - New `CachifyPoolFullError` exception exported from `py_cachify`.

#### **Configurable lock polling interval**:
  - `init_cachify` now accepts a `lock_poll_interval` parameter (default: `0.1` seconds).
  - This controls how frequently the library polls for lock availability when `nowait=False`.
  - Lower values make lock acquisition more responsive but increase load on the cache backend.
  - Higher values reduce backend load but may increase wait times.

#### **Thread-safe async memory cache**:
  - The in-memory async cache wrapper (`AsyncWrapper`) now uses an `asyncio.Lock` to protect concurrent access.
  - This prevents race conditions when multiple async tasks access the same in-memory cache simultaneously.

### Improvements

- Minor code cleanup in `MemoryCache.delete()` for better efficiency.

---

## [3.0.1](https://github.com/EzyGang/py-cachify/releases/tag/v3.0.1)

- Same code as 3.0.0, published under a new version number: 3.0.0 is not on PyPI, so 3.0.1 is the first 3.x release you can install. The notes for 3.0.0 below apply.

---

## [3.0.0](https://github.com/EzyGang/py-cachify/releases/tag/v3.0.0)

In short, 3.0.0 focuses on:

- Instance-based usage (`Cachify`) and multiple independent caches per app.
- Stronger locking semantics backed by atomic `nx` support in cache clients.
- A configurable `default_cache_ttl` with clearer TTL precedence rules.
- Cleanup of long-deprecated aliases and stricter type checking on modern Python versions.
- Documentation updates and improvements, including a separate page to use with Agentic systems and LLMs.

### Features & Enhancements

#### **Multiple cachify instances per app**:
  - `init_cachify` now supports `is_global: bool = True` and returns a `Cachify` instance.
  - When `is_global=True` (default), `init_cachify` configures the global client used by top-level `cached`, `lock`, and `once` and returns a `Cachify` instance backed by that client.
  - When `is_global=False`, `init_cachify` does **not** modify the global client and instead returns an independent `Cachify` instance exposing:
    - `Cachify.cached(...)`
    - `Cachify.lock(...)`
    - `Cachify.once(...)`

#### **New public `Cachify` type**:
  - `Cachify` is now publicly exported from `py_cachify`.
  - It provides a convenient, instance-scoped API over the same high-level decorators:
    - `@Cachify.cached(...)`
    - `@Cachify.lock(...)`
    - `@Cachify.once(...)`
  - All instance methods share the same semantics as the corresponding top-level decorators, but are bound to a specific client/prefix.

#### **Improved reset and lock-query semantics in helpers**:
  - The helper functions `reset`, `a_reset`, `is_locked`, and `is_alocked` have been reworked to:
    - Accept internal parameters (`_pyc_key`, `_pyc_signature`, `_pyc_operation_postfix`, `_pyc_original_func`, `_pyc_client_provider`) to make them fully aware of which client and which wrapped function they are operating on and prevent collisions with user defined functions args and kwargs.

#### **Configurable default cache TTL**:
  - `init_cachify` and `Cachify` now accept an optional `default_cache_ttl` parameter.
  - If a `@cached` decorator does **not** specify `ttl`, the `default_cache_ttl` of the underlying client is used as the fallback.
  - Passing `ttl=None` to `@cached` now explicitly means “no expiration”, even if `default_cache_ttl` is set.
  - Effective TTL precedence:
    1. If `@cached(ttl=...)` is provided, that value is used.
    2. Else, if the client has `default_cache_ttl` set, that value is used.
    3. Else, entries are stored without expiration.

#### **Stronger lock correctness with atomic `nx` support**:
  - Lock acquisition and the `once` decorator now rely on an atomic “set-if-not-exists” (`nx`) operation provided by the underlying cache client.
  - Built-in clients (in-memory, Redis examples) have been updated to implement `set(..., nx=True)` semantics for lock keys.
  - This significantly reduces race conditions in concurrent environments and makes lock behavior more predictable.

#### **Multi-layer caching support**:
  - Thanks to the helper changes and the instance-scoped API, it is now straightforward to stack multiple `cached` decorators, for example:
    - A global cache with a long TTL; and
    - A local instance cache with a shorter TTL on top of it.
  - Calling `reset(*args, **kwargs)` on the outermost wrapper will:
    - Clear that wrapper’s cache entry; and
    - Attempt to call `reset` on the inner wrapper(s), if they expose such a method, so the entire “stack” is reset for the given arguments.
  - This pattern is documented in the updated `cached` reference and tutorial.

#### **Stricter typing and tooling**:
  - Python baseline bumped to **3.9+**.
  - Core types updated to use `collections.abc.Awaitable` and built-in generics (`dict[...]`, `tuple[...]`, etc.).
  - `typing-extensions` dependency bumped (>=4.15.0) and `basedpyright` configuration added for strict type checking on the `py_cachify` package.

### Breaking Changes

#### **Deprecated aliases removed**:
  - The following deprecated functions, announced in 2.0.0 as scheduled for removal in 3.0.0, have now been removed:
    - `async_cached`
    - `sync_cached`
    - `async_once`
    - `sync_once`
  - Use the unified decorators instead:
    - `cached` for both sync and async caching.
    - `once` for both sync and async “once at a time” locking.

#### **Python 3.8 support dropped**:
  - The supported Python versions are now 3.9–3.14.
  - Python 3.8 is no longer supported and is removed from classifiers and test matrix.

### Notes on Migration from 2.x to 3.0.0

#### If you implemented (used) a custom cache client:
  - Ensure your client supports an atomic "set-if-not-exists" semantics used by locks and `once`.
  - Concretely, the client should implement a `set(key, value, ttl=None, nx=False)` (or equivalent) method where:
    - `nx=False` behaves like a normal set; and
    - `nx=True` only sets the value if the key does *not* already exist, returning an appropriate success indicator.
  - Without `nx` semantics, lock and `once` behavior may no longer be correct in 3.0.0.

#### If you only used:
  - `init_cachify(...)`,
  - `cached`,
  - `lock`,
  - `once`,
  and **did not** use any of the deprecated aliases or internal APIs, you should be able to upgrade with no code changes.
#### If you used any of the deprecated aliases:
  - Replace:
    - `sync_cached` / `async_cached` with `cached` (it works for both sync and async).
    - `sync_once` / `async_once` with `once`.

---

## [2.1.1](https://github.com/EzyGang/py-cachify/releases/tag/v2.1.1)

### Features & Enhancements

- Python 3.14 support.
- Sync wrappers of `cached`, `lock` and `once` keep the wrapped function's return type for type checkers.
- Bump dependencies.

## [2.1.0](https://github.com/EzyGang/py-cachify/releases/tag/v2.1.0)

### Features & Enhancements

- **Operation postfix in keys**: every key now ends with the operation that made it: `-cached`, `-lock` or `-once`. A `cached`, a `lock` and a `once` with the same key template no longer share, and overwrite, one entry.
- All modules log through one `py-cachify` logger (`logging.getLogger('py-cachify')`).
- Bump dependencies; development moved from Poetry to uv.

### Upgrade notes

- Because keys changed, values cached by 2.0.x aren't found after the upgrade (each key is computed once more), and a lock held by a 2.0.x process isn't seen by a 2.1.0 process. Avoid running both versions side by side against the same backend.

## [2.0.10](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.10) 

### Features & Enchancements

- Default log level is now DEBUG
- Dependencies bump

## [2.0.9](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.9) 

### Features & Enchancements

- Better error message on the mismatch of key format params and function arguments

### Bugfixes

- Fix default arguments are not respected when crafting cache key

## [2.0.8](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.8)

### Features & Enhancements

- Bump dependencies

## [2.0.7](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.7) 

### Features & Enchancements

- Bump dependencies
- Add Python 3.13 Support

## [2.0.5](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.5)

### Features & Enhancements

- Add Python 3.13 support
- Bump dependencies

## [2.0.4](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.4) 

### Features & Enchancements

- Bump dependencies
- Better README and Docs

## [2.0.3](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.3)

### Miscellaneous

- Documentation fixes

## [2.0.2](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.2)

### Features & Enhancements

- Bump dependencies
- README and documentation tweaks

## [2.0.1](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.1)

### Features & Enhancements

- **Typing adjustments**: names are re-exported explicitly (`from ... import x as x`) instead of through `__all__`, so strict type checkers accept imports from `py_cachify`.
- `AsyncLockWrappedF`, `SyncLockWrappedF` and `WrappedFunctionLock` are exported from `py_cachify`.
- Functions wrapped with `cached` (sync) and `lock` keep their return type instead of `Any`.

### Miscellaneous

- Documentation and README update

## [2.0.0](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.0)

### Features & Enchancements
- **Lock improvements**: Locks are now way more versatile and support new parameters like:
    - Whether to wait for the lock to expire or not (`nowait`, boolean)
    - Timeouts for how long should it try to acquire a lock. (`timeout`, int | float | None)
    - Expiration param to prevent deadlocks (`exp`, int | None)
    - When using lock as a decorator or using `once` decorator two methods are being added to the wrapped function:
        - `is_locked(*args, **kwargs)` - to check whether the lock is acquired or not
        - `release(*args, **kwargs)` - to forcefully release a lock.
    
    - More info could be found in the [lock reference](./reference/lock.md).
  
- **File layout improved**: All internal files have been made private helping LSP's and IDE's 
provide better import locations for the features py-cachify provides.

- **Type annotations now feature TypeIs & Protocols**: Updated type annotations now provide even better IDE support, 
making it easier to write better code. They expose all methods attached to decorated functions and help you inline.

- **Additional tests were added**

- **`cached` decorator improvements**: There is now a new method attached to the wrapped functions called
`reset(*args, **kwargs)` to allow for a quick cache resets.
    - More info can be found in the [cached reference](./reference/cached.md).
    
- **Bump dependencies**

### Breaking Changes
- **async_lock**: Async lock has been removed, you should replace it with `lock` since it now can work in both contexts.
- **import locations**: since files were renamed and moved around quite a bit, 
some import locations may not work after the 2.0.0 release, so I recommend reimporting used functions to ensure they work in your project.
### Deprecations
- **async_once, sync_once, async_cached, sync_cached**: These are now deprecated and scheduled for removal in 3.0.0
(all of those methods are just aliases for `cached` and `once`). 

### Miscellaneous
- **Documentation**: Documentation was refactored and greatly improved.

I recommend checking out **[full API reference](reference/init.md)** to get familiar with changes and new features.

## [1.1.2](https://github.com/EzyGang/py-cachify/releases/tag/v1.1.2)

### Features & Enchancements
- **Bump dependencies**
- **Docs update to include info on `init_cachify` `prefix` parameter**


## [1.1.0](https://github.com/EzyGang/py-cachify/releases/tag/v1.1.0)
### Features & Enchancements
- **Custom encoders/decoders for the `cached` decorator**: `enc_dec` parameter introduced on a `cached` decorator.

### Miscellaneous
- **Documentation update**

## [1.0.11](https://github.com/EzyGang/py-cachify/releases/tag/v1.0.11)

### Features & Enhancements
- **Client protocol**: `get` on `SyncClient` and `AsyncClient` (and the built-in memory cache) takes only the key, `get(name)`, and returns the value or `None`; the `default` argument is gone, matching redis-py.
- **Bump dependencies**

## [1.0.10](https://github.com/EzyGang/py-cachify/releases/tag/v1.0.10)

### Breaking Changes
- **`py_cachify.async` renamed to `py_cachify.asyncio`**: `async` is a Python keyword, so `from py_cachify.async import ...` was a syntax error. Import the async decorators from `py_cachify.asyncio`.

## [1.0.9](https://github.com/EzyGang/py-cachify/releases/tag/v1.0.9)

### Features & Enhancements
- **Bump dependencies**

### Miscellaneous
- **Documentation update**

## [1.0.8](https://github.com/EzyGang/py-cachify/releases/tag/v1.0.8)

### Features & Enhancements
- **Sync and async decorators split**: `py_cachify.sync` exports `sync_cached`, `sync_once`, `lock` and `SyncClient`; `py_cachify.async` exports `async_cached`, `async_once`, `async_lock` and `AsyncClient`. Type checkers complain less when each decorator matches the kind of function it wraps.

### Breaking Changes
- **Imports**: `lock`, `async_lock`, `SyncClient` and `AsyncClient` are no longer importable from `py_cachify` itself; import them from the new modules. `cached`, `once`, `init_cachify` and the exceptions stay at the top level.

## [1.0.7](https://github.com/EzyGang/py-cachify/releases/tag/v1.0.7)

### Features & Enhancements
- **Generic return types**: decorated functions keep their return type for type checkers.

### Miscellaneous
- **README**

## [1.0.6](https://pypi.org/project/py-cachify/1.0.6/)

### Features & Enhancements
- **`py.typed` marker**: type checkers now use the package's own annotations.

## [1.0.5](https://pypi.org/project/py-cachify/1.0.5/)

### Bugfixes
- **Client protocol annotations**: `SyncClient` and `AsyncClient` use `typing.Protocol` and a valid `Union[int, None]` for `ex`.

### Miscellaneous
- **Bump dependencies, typo fixes**

## [1.0.4](https://pypi.org/project/py-cachify/1.0.4/)

### Features & Enhancements
- **Bump dependencies**

## [1.0.3](https://pypi.org/project/py-cachify/1.0.3/)

### Features & Enhancements
- **Key prefix**: `init_cachify(prefix=...)` prepends a prefix to every key (default `'_PYC_'`).
- **Pickled values**: values are pickled before they are stored, so any picklable object can be cached in Redis.
- **`SyncClient` and `AsyncClient` protocols** are exported, for custom clients.

### Miscellaneous
- **Documentation** and integration tests against Redis

## [1.0.2](https://pypi.org/project/py-cachify/1.0.2/)

First release on PyPI: `init_cachify`, the `cached` decorator, `lock`, `async_lock` and `once`, an in-memory cache by default, and the `CachifyInitError` and `CachifyLockError` exceptions.
