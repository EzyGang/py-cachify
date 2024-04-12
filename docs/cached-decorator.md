# `cached` decorator

The cached decorator is designed to cache the result of a function and retrieve the cached result for subsequent calls, based on a specified key. 
It also supports setting a time-to-live (TTL) for the cached values. 

The returned function value should be picklable, i.e. a pydantic's `BaseModel`
subclasses are picklable, but a Django's `Response` is not. There is an [issue](https://github.com/EzyGang/py-cachify/issues/46) present to implement an ability
to provide custom encoders/decoders to extend the possible applications.

It detects the type of function that it is being applied to automatically using a compatible cache client for it (sync or async).


__TYPE CHECKING__: Currently there is no way (*or we haven't found one*) to correctly type annotate a decorator so that you won't have to ignore or cast
the results of a function the decorator is being applied to. In order to use specific decorator to match
your runtime you can import the desired one with:
```python
from py_cachify.sync import sync_cached
# OR for async
from py_cachify.async import async_cached

```

### Parameters

| Param name | Param type            | Description                                                                                                                                                                      | Default |
|------------|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| `key`      | `str`                 | The unique identifier used to determine whether the function has already been executed. The key can be a string containing placeholders to be formatted with function arguments. |         |
| `ttl`      | `int, None, optional` | Time-to-live for the cached value in seconds. If None, the value is cached indefinitely.                                                                                         | `None`  |


### Usage
```python
from py_cachify import cached

@cached(key='example_key', ttl=60)
def expensive_function(x):
    print('Executing expensive operation...')
    return x ** 2


@cached(key='example_async_function-{arg_a}-{arg_b}')
def async_expensive_function(arg_a: int, arg_b: int) -> int:
    return arg_a + arg_b

```

The cached decorator is applied to a function, ensuring that the decorated function's result is cached for subsequent calls.

It checks the cache for the result using the specified key. If the result is found, 
it is returned; otherwise, the original function is executed, and the result is stored in the cache.

The `ttl` parameter allows setting a time-to-live for the cached value. 
If provided (in the first example), the cached value will be automatically invalidated after the specified time.
