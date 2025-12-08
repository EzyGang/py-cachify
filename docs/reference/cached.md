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
| `ttl`               | `Union[int, None]`, optional    | Time-to-live for the cached result, in seconds. Defaults to `None`, which means the cache does not expire.   |
| `enc_dec`           | `Union[Tuple[Encoder, Decoder], None]`, optional  | A tuple containing the encoding and decoding functions for the cached value. Defaults to `None`, which means that no encoding or decoding functions will be applied. |

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
from py_cachify import cached


@cached('my_cache_key', ttl=60)
def compute_expensive_operation(param):
    # Imagine an expensive computation here
    return param * 2


@cached('my_async_cache_key-{param}', ttl=30)
async def fetch_data(param):
    # Imagine an async operation to fetch data
    return {'data': param}
```

### Instance-based Usage

If you need multiple independent caches (for example, per module or subsystem), you can create dedicated `Cachify` instances via `init_cachify(is_global=False)` and use their `cached` method instead of the global decorator.

```python
from py_cachify import init_cachify

# Create a dedicated instance that does not affect the global client
local_cachify = init_cachify(is_global=False, prefix='LOCAL-')

@local_cachify.cached(key='local-{x}-{y}', ttl=10)
def local_sum(x: int, y: int) -> int:
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