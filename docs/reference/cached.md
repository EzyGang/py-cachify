# API Reference for ///@cached()/// Decorator

## Overview

The `cached` decorator provides a caching mechanism that stores the result of a function based on a specified key, time-to-live (TTL), and optional encoding/decoding functions. It can be applied to both synchronous and asynchronous functions, facilitating quick access to previously computed results.

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

| `ttl`               | `Union[int, None]`, optional    | Time-to-live (seconds) for the cached result. If omitted, the decorator uses the cache client's `default_cache_ttl` (configured via `init_cachify`). If `ttl` is `None`, the value is stored without expiration. If `ttl` is an integer, that value is used directly.   |
| `enc_dec`           | `Union[Tuple[Encoder, Decoder], None]`, optional  | A tuple containing the encoding and decoding functions for the cached value. Defaults to `None`, which means that no encoding or decoding functions will be applied. |


### Default TTL behavior

The effective TTL for a cached value is determined as follows:

1. If you pass an explicit integer, for example `@cached(..., ttl=30)`, that TTL is used.
2. If you pass `ttl=None`, the cache entry is stored **without expiration** (infinite TTL in most backends).
3. If you omit `ttl` entirely, the decorator will fall back to the underlying client's `default_cache_ttl`:
   - `default_cache_ttl` is configured via `init_cachify(default_cache_ttl=...)` for both global and instance-based usage.
   - If `default_cache_ttl` is `None` (the default), omitting `ttl` behaves like “no expiration”.

This lets you define a global or instance-specific default TTL once and only override it where needed.

### Returns

- `WrappedFunctionReset`: A wrapped function (either synchronous or asynchronous) with an additional `reset` method attached for cache management. The `reset(*args, **kwargs)` method allows the user to manually reset the cache for the function using the same key.

### Method Behavior

1. **For Synchronous Functions**:
    - Checks if a cached value exists for the provided key.
    - If the cached value exists, it returns the decoded value.
    - If not, it executes the function, caches the result (after encoding, if specified), and then returns the result.

2. **For Asynchronous Functions**:
    - Similar checks are performed in an asynchronous context using `await`.
    - The caching behavior mirrors the synchronous version.

### Global Usage Example

```python
from py_cachify import cached, init_cachify


# Configure a default cache TTL of 60 seconds for all cached values
init_cachify(default_cache_ttl=60)


@cached('my_cache_key')
def compute_expensive_operation(param):
    # Uses default_cache_ttl=60 as TTL
    return param * 2


@cached('my_async_cache_key-{param}', ttl=30)
async def fetch_data(param):
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