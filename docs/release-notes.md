# Release Notes

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

## [2.0.10](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.10) 

### Features & Enchancements

- Default log level is now DEBUG
- Dependencies bump

## [2.0.9](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.9) 

### Features & Enchancements

- Better error message on the mismatch of key format params and function arguments

### Bugfixes

- Fix default arguments are not respected when crafting cache key

## [2.0.7](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.7) 

### Features & Enchancements

- Bump dependencies
- Add Python 3.13 Support

## [2.0.4](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.4) 

### Features & Enchancements

- Bump dependencies
- Better README and Docs

## [2.0.0](https://github.com/EzyGang/py-cachify/releases/tag/v2.0.0)

### Features & Enchancements
- **Lock improvements**: Locks are now way more versatile and support new parameters like:
    - Whether to wait for the lock to expire or not (`nowait`, boolean)
    - Timeouts for how long should it try to acquire a lock. (`timeout`, int | float | None)
    - Expiration param to prevent deadlocks (`exp`, int | None)
    - When using lock as a decorator or using `once` decorator two methods are being added to the wrapped function:
        - `is_locked(*args, **kwargs)` - to check whether the lock is acquired or not
        - `release(*args, **kwargs)` - to forcefully release a lock.
    
    - More info could be found [here](./reference/lock.md).
  
- **File layout improved**: All internal files have been made private helping LSP's and IDE's 
provide better import locations for the features py-cachify provides.

- **Type annotations now feature TypeIs & Protocols**: Updated type annotations now provide even better IDE support, 
making it easier to write better code. They expose all methods attached to decorated functions and help you inline.

- **Additional tests were added**

- **`cached` decorator improvements**: There is now a new method attached to the wrapped functions called
`reset(*args, **kwargs)` to allow for a quick cache resets.
    - More info can be found [here](./reference/cached.md).
    
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


## [1.1.0](https://github.com/EzyGang/py-cachify/releases/tag/v1.1.2)
### Features & Enchancements
- **Custom encoders/decoders for the `cached` decorator**: `enc_dec` parameter introduced on a `cached` decorator.

### Miscellaneous
- **Documentation update**
