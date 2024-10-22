# API Reference for ///@cached()/// Decorator

## Overview

The `cached` decorator provides a caching mechanism that stores the result of a function based on a specified key, 
time-to-live (TTL), and optional encoding/decoding functions. 
It can be applied to both synchronous and asynchronous functions, facilitating quick access to previously computed results.

---

## Function: ///cached///

### Description
The `cached` decorator caches the results of a function execution using a unique key.
If the function is called again with the same key before the TTL expires, 
the cached result is returned instead of re-executing the function. This is particularly useful for expensive computations or IO-bound tasks.

### Parameters

| Parameter            | Type                            | Description                                                                                                   |
|---------------------|---------------------------------|---------------------------------------------------------------------------------------------------------------|
| `key`               | `str`                           | The key used to identify the cached result, which can utilize formatted strings to create dynamic keys. (i.e. `key='my_key-{func_arg}'`)       |
| `ttl`               | `Union[int, None]`, optional    | Time-to-live for the cached result, in seconds. Defaults to `None`, which means the cache does not expire.   |
| `enc_dec`           | `Union[Tuple[Encoder, Decoder], None]`, optional  | A tuple containing the encoding and decoding functions for the cached value. Defaults to `None`, which means that no encoding or decoding functions will be applied. |

### Returns
- `WrappedFunctionReset`: A wrapped function (either synchronous or asynchronous) with an additional `reset` method attached for cache management. 
The `reset(*args, **kwargs)` method allows the user to manually reset the cache for the function using the same key.

### Method Behavior
1. **For Synchronous Functions**:
    - Checks if a cached value exists for the provided key.
    - If the cached value exists, it returns the decoded value.
    - If not, it executes the function, caches the result (after encoding, if specified), and then returns the result.

2. **For Asynchronous Functions**:
    - Similar checks are performed in an asynchronous context using `await`.
    - The caching behavior mirrors the synchronous version.

### Usage Example

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

### Resetting the Cache
You can reset the cache for either a synchronous or asynchronous function by calling the `reset` method attached to the wrapped function.

```python
# Reset cache for a synchronous function
compute_expensive_operation.reset()

# Reset cache for an asynchronous function
await fetch_data.reset(param='param-value')
```

### Notes

- Ensure that both the serialization and deserialization functions defined in `enc_dec` are efficient to preserve optimal performance.
- If py-cachify is not initialized through `init_cachify`, a `CachifyInitError` will be raised.

### Type Hints Remark

Currently, Python's type hints have limitations in fully capturing a function's 
original signature when transitioning to a protocol-based callable in a decorator, 
particularly for methods (i.e., those that include `self`). 
`ParamSpec` can effectively handle argument and keyword types for functions 
but doesn't translate well to methods within protocols like `WrappedFunctionReset`. 
I'm staying updated on this issue and recommend checking the following resources 
for more insights into ongoing discussions and proposed solutions:

- [Typeshed Pull Request #11662](https://github.com/python/typeshed/pull/11662)
- [Mypy Pull Request #17123](https://github.com/python/mypy/pull/17123)
- [Python Discussion on Allowing Self-Binding for Generic ParamSpec](https://discuss.python.org/t/allow-self-binding-for-generic-paramspec/50948)

Once any developments occur, I will quickly update the source code to incorporate the changes.